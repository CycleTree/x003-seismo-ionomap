from __future__ import annotations

import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.processing.grid import GridProcessingConfig, build_tec_grid, export_tec_grid, load_ipp_points


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate IPP/VTEC points into a time-space TEC grid.")
    parser.add_argument("input_ipp_points", help="Path to IPP points parquet")
    parser.add_argument("--output-dir", default="data/intermediate/tec_grid")
    parser.add_argument("--time-step", default="15min")
    parser.add_argument("--lat-resolution-deg", type=float, default=0.5)
    parser.add_argument("--lon-resolution-deg", type=float, default=0.5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    ipp_points = load_ipp_points(args.input_ipp_points)
    grid = build_tec_grid(
        ipp_points,
        GridProcessingConfig(
            time_step=args.time_step,
            lat_resolution_deg=args.lat_resolution_deg,
            lon_resolution_deg=args.lon_resolution_deg,
        ),
    )
    input_path = Path(args.input_ipp_points)
    artifacts = export_tec_grid(
        grid,
        output_dir=args.output_dir,
        prefix=input_path.stem.replace(".ipp_points", ""),
    )
    print(f"rows={len(grid)}")
    print(f"output={artifacts.output_path}")


if __name__ == "__main__":
    main()
