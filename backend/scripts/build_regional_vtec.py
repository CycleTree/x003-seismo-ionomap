from __future__ import annotations

import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.processing.regional_vtec import (
    RegionalVtecConfig,
    build_regional_vtec_grid,
    build_regional_vtec_grid_from_parquet,
    export_regional_vtec_grid,
    load_ipp_points,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build regularized regional VTEC grid from IPP points.")
    parser.add_argument("input_parquet", help="Path to ipp_points parquet")
    parser.add_argument("--output-dir", default="data/intermediate/tec_grid")
    parser.add_argument("--time-step", default="15min")
    parser.add_argument("--lat-resolution-deg", type=float, default=0.5)
    parser.add_argument("--lon-resolution-deg", type=float, default=0.5)
    parser.add_argument("--lat-min-deg", type=float, default=20.0)
    parser.add_argument("--lat-max-deg", type=float, default=50.0)
    parser.add_argument("--lon-min-deg", type=float, default=120.0)
    parser.add_argument("--lon-max-deg", type=float, default=155.0)
    parser.add_argument("--smoothing-lambda", type=float, default=0.25)
    parser.add_argument("--streaming", action="store_true", help="Read parquet one time bin at a time")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_path = Path(args.input_parquet)
    config = RegionalVtecConfig(
        time_step=args.time_step,
        lat_resolution_deg=args.lat_resolution_deg,
        lon_resolution_deg=args.lon_resolution_deg,
        lat_min_deg=args.lat_min_deg,
        lat_max_deg=args.lat_max_deg,
        lon_min_deg=args.lon_min_deg,
        lon_max_deg=args.lon_max_deg,
        smoothing_lambda=args.smoothing_lambda,
    )
    if args.streaming:
        grid = build_regional_vtec_grid_from_parquet(input_path, config)
    else:
        ipp_points = load_ipp_points(input_path)
        grid = build_regional_vtec_grid(
            ipp_points,
            config,
        )
    artifacts = export_regional_vtec_grid(
        grid,
        output_dir=args.output_dir,
        prefix=input_path.stem.replace(".ipp_points", ""),
    )
    print(f"rows={len(grid)}")
    print(f"output={artifacts.output_path}")


if __name__ == "__main__":
    main()
