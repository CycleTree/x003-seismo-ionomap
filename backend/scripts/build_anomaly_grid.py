from __future__ import annotations

import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.processing.anomaly import (
    AnomalyProcessingConfig,
    build_anomaly_grid,
    export_anomaly_grid,
    load_tec_grid,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build anomaly grid metrics from aggregated TEC grid.")
    parser.add_argument("input_tec_grid", help="Path to TEC grid parquet")
    parser.add_argument("--output-dir", default="data/intermediate/anomaly_grid")
    parser.add_argument("--std-floor-tecu", type=float, default=0.1)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    tec_grid = load_tec_grid(args.input_tec_grid)
    anomaly_grid = build_anomaly_grid(
        tec_grid,
        AnomalyProcessingConfig(std_floor_tecu=args.std_floor_tecu),
    )
    input_path = Path(args.input_tec_grid)
    artifacts = export_anomaly_grid(
        anomaly_grid,
        output_dir=args.output_dir,
        prefix=input_path.stem.replace(".tec_grid", ""),
    )
    print(f"rows={len(anomaly_grid)}")
    print(f"output={artifacts.output_path}")


if __name__ == "__main__":
    main()
