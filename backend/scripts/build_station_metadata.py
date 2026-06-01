from __future__ import annotations

import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.processing.station_metadata import export_station_metadata, parse_qc_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build station metadata parquet from RINGO QC summary.")
    parser.add_argument("input_qc", help="Path to ringo qc summary log")
    parser.add_argument("--output-dir", default="data/intermediate/stations")
    parser.add_argument("--station-id", default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    metadata = parse_qc_summary(args.input_qc)
    if args.station_id:
        metadata["station_id"] = args.station_id
    prefix = str(metadata["station_id"])
    artifacts = export_station_metadata(metadata, output_dir=args.output_dir, prefix=prefix)
    print(f"station_id={metadata['station_id']}")
    print(f"output={artifacts.output_path}")


if __name__ == "__main__":
    main()
