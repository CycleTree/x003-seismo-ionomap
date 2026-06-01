from __future__ import annotations

import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.processing.ipp import (
    IppProcessingConfig,
    build_ipp_points,
    export_ipp_points,
    load_station_metadata,
)
from app.processing.stec import load_stec_arcs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build IPP/VTEC points from leveled STEC arcs and station metadata.")
    parser.add_argument("input_stec_arcs", help="Path to stec arc parquet")
    parser.add_argument("station_metadata", help="Path to station metadata parquet")
    parser.add_argument("--output-dir", default="data/intermediate/ipp_points")
    parser.add_argument("--shell-height-km", type=float, default=350.0)
    parser.add_argument("--min-elevation-deg", type=float, default=15.0)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = IppProcessingConfig(
        shell_height_km=args.shell_height_km,
        min_elevation_deg=args.min_elevation_deg,
    )
    stec_arcs = load_stec_arcs(args.input_stec_arcs)
    station_metadata = load_station_metadata(args.station_metadata)
    ipp_points = build_ipp_points(stec_arcs, station_metadata, config)
    input_path = Path(args.input_stec_arcs)
    artifacts = export_ipp_points(
        ipp_points,
        output_dir=args.output_dir,
        prefix=input_path.stem.replace(".stec_arcs", ""),
    )
    print(f"rows={len(ipp_points)}")
    print(f"output={artifacts.output_path}")


if __name__ == "__main__":
    main()
