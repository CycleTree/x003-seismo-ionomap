from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.processing.anomaly import (
    AnomalyProcessingConfig,
    build_anomaly_grid,
    export_anomaly_grid,
    load_baseline_tec_grids,
)
from app.processing.multi_station import (
    StationProcessingConfig,
    collect_station_pairs,
    ensure_output_directories,
    merge_ipp_point_files,
    run_station_batch,
)
from app.processing.regional_vtec import RegionalVtecConfig, build_regional_vtec_grid, export_regional_vtec_grid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run tests, then execute the multi-station national pipeline.")
    parser.add_argument("raw_dir", help="Directory containing *.26d.gz and *.26N.tar.gz")
    parser.add_argument("--output-root", default="/data/intermediate/national_run")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--max-stations", type=int, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--gap-seconds", type=float, default=300.0)
    parser.add_argument("--phase-jump-threshold-tecu", type=float, default=2.0)
    parser.add_argument("--min-arc-points", type=int, default=10)
    parser.add_argument("--shell-height-km", type=float, default=350.0)
    parser.add_argument("--min-elevation-deg", type=float, default=15.0)
    parser.add_argument("--min-s1-dbhz", type=float, default=None)
    parser.add_argument("--min-s2-dbhz", type=float, default=None)
    parser.add_argument("--max-abs-code-geometry-free-m", type=float, default=None)
    parser.add_argument("--time-step", default="15min")
    parser.add_argument("--lat-resolution-deg", type=float, default=0.5)
    parser.add_argument("--lon-resolution-deg", type=float, default=0.5)
    parser.add_argument("--lat-min-deg", type=float, default=20.0)
    parser.add_argument("--lat-max-deg", type=float, default=50.0)
    parser.add_argument("--lon-min-deg", type=float, default=120.0)
    parser.add_argument("--lon-max-deg", type=float, default=155.0)
    parser.add_argument("--smoothing-lambda", type=float, default=0.25)
    parser.add_argument("--std-floor-tecu", type=float, default=0.1)
    parser.add_argument("--baseline-grid", action="append", default=[], help="Quiet-day TEC grid parquet path")
    parser.add_argument("--local-time-offset-hours", type=float, default=9.0)
    return parser


def run_tests() -> None:
    subprocess.run([sys.executable, "-m", "pytest", "tests"], cwd=BACKEND_ROOT, check=True)


def main() -> None:
    args = build_parser().parse_args()
    if not args.skip_tests:
        run_tests()

    output_root = Path(args.output_root)
    ensure_output_directories(output_root)

    pairs = collect_station_pairs(args.raw_dir)
    if args.max_stations is not None:
        pairs = pairs[: args.max_stations]
    if not pairs:
        raise SystemExit("No station pairs found")

    ipp_paths = run_station_batch(
        pairs,
        StationProcessingConfig(
            output_root=output_root,
            gap_seconds=args.gap_seconds,
            phase_jump_threshold_tecu=args.phase_jump_threshold_tecu,
            min_arc_points=args.min_arc_points,
            shell_height_km=args.shell_height_km,
            min_elevation_deg=args.min_elevation_deg,
            min_s1_dbhz=args.min_s1_dbhz,
            min_s2_dbhz=args.min_s2_dbhz,
            max_abs_code_geometry_free_m=args.max_abs_code_geometry_free_m,
        ),
        max_workers=args.workers,
    )

    merged_ipp = merge_ipp_point_files(ipp_paths)
    national_ipp_path = output_root / "national" / "national.ipp_points.parquet"
    merged_ipp.to_parquet(national_ipp_path, index=False)

    tec_grid = build_regional_vtec_grid(
        merged_ipp,
        RegionalVtecConfig(
            time_step=args.time_step,
            lat_resolution_deg=args.lat_resolution_deg,
            lon_resolution_deg=args.lon_resolution_deg,
            lat_min_deg=args.lat_min_deg,
            lat_max_deg=args.lat_max_deg,
            lon_min_deg=args.lon_min_deg,
            lon_max_deg=args.lon_max_deg,
            smoothing_lambda=args.smoothing_lambda,
        ),
    )
    tec_grid_artifacts = export_regional_vtec_grid(tec_grid, output_dir=output_root / "tec_grid", prefix="national")

    baseline_grid = load_baseline_tec_grids(args.baseline_grid)
    anomaly_grid = build_anomaly_grid(
        tec_grid,
        AnomalyProcessingConfig(
            std_floor_tecu=args.std_floor_tecu,
            local_time_offset_hours=args.local_time_offset_hours,
        ),
        baseline_grid=baseline_grid,
    )
    anomaly_artifacts = export_anomaly_grid(
        anomaly_grid,
        output_dir=output_root / "anomaly_grid",
        prefix="national",
    )

    print(f"stations={len(pairs)}")
    print(f"ipp_files={len(ipp_paths)}")
    print(f"national_ipp={national_ipp_path}")
    print(f"tec_grid={tec_grid_artifacts.output_path}")
    print(f"anomaly_grid={anomaly_artifacts.output_path}")


if __name__ == "__main__":
    main()
