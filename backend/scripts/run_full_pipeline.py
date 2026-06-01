from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config.gnss import IngestConfig
from app.processing.anomaly import AnomalyProcessingConfig, build_anomaly_grid, export_anomaly_grid
from app.processing.grid import GridProcessingConfig, build_tec_grid, export_tec_grid
from app.processing.ipp import IppProcessingConfig, build_ipp_points, export_ipp_points, load_station_metadata
from app.processing.ringo_ingest import (
    export_observation_products,
    load_ringo_csv,
    normalize_wide_observations,
    select_priority_observations,
    wide_to_long_observations,
)
from app.processing.station_metadata import export_station_metadata, parse_qc_summary
from app.processing.stec import StecProcessingConfig, build_stec_arcs, export_stec_arcs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run tests, then execute the full preprocessing pipeline.")
    parser.add_argument("ringo_csv", help="Path to RINGO rnxcsv output with az/el columns")
    parser.add_argument("qc_log", help="Path to RINGO QC summary log")
    parser.add_argument("--station-id", default=None, help="Station identifier override")
    parser.add_argument("--output-root", default="data/intermediate")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--gap-seconds", type=float, default=300.0)
    parser.add_argument("--phase-jump-threshold-tecu", type=float, default=2.0)
    parser.add_argument("--min-arc-points", type=int, default=10)
    parser.add_argument("--shell-height-km", type=float, default=350.0)
    parser.add_argument("--min-elevation-deg", type=float, default=15.0)
    parser.add_argument("--time-step", default="15min")
    parser.add_argument("--lat-resolution-deg", type=float, default=0.5)
    parser.add_argument("--lon-resolution-deg", type=float, default=0.5)
    parser.add_argument("--std-floor-tecu", type=float, default=0.1)
    return parser


def derive_station_id(ringo_csv: Path, explicit: str | None, qc_station_id: str | None) -> str:
    if explicit:
        return explicit
    if qc_station_id:
        return qc_station_id
    config = IngestConfig()
    return config.default_station_id or ringo_csv.stem.split(".")[0]


def run_tests() -> None:
    subprocess.run([sys.executable, "-m", "pytest", "tests"], cwd=BACKEND_ROOT, check=True)


def main() -> None:
    args = build_parser().parse_args()
    if not args.skip_tests:
        run_tests()

    output_root = Path(args.output_root)
    ringo_csv_path = Path(args.ringo_csv)
    qc_log_path = Path(args.qc_log)

    station_metadata_dict = parse_qc_summary(qc_log_path)
    station_id = derive_station_id(ringo_csv_path, args.station_id, str(station_metadata_dict.get("station_id")))
    station_metadata_dict["station_id"] = station_id

    ringo_frame = load_ringo_csv(ringo_csv_path)
    wide = normalize_wide_observations(ringo_frame, station_id=station_id, source_path=ringo_csv_path)
    long_frame = wide_to_long_observations(wide)
    selected = select_priority_observations(wide, IngestConfig().observation_priority)
    export_observation_products(
        wide=wide,
        long_frame=long_frame,
        selected=selected,
        output_dir=output_root / "observations",
        prefix=ringo_csv_path.stem,
    )

    stec_arcs = build_stec_arcs(
        selected,
        StecProcessingConfig(
            gap_seconds=args.gap_seconds,
            phase_jump_threshold_tecu=args.phase_jump_threshold_tecu,
            min_arc_points=args.min_arc_points,
        ),
    )
    stec_artifacts = export_stec_arcs(
        stec_arcs,
        output_dir=output_root / "stec_arcs",
        prefix=ringo_csv_path.stem,
    )

    station_artifacts = export_station_metadata(
        station_metadata_dict,
        output_dir=output_root / "stations",
        prefix=station_id,
    )
    station_metadata = load_station_metadata(station_artifacts.output_path)
    ipp_points = build_ipp_points(
        stec_arcs,
        station_metadata,
        IppProcessingConfig(
            shell_height_km=args.shell_height_km,
            min_elevation_deg=args.min_elevation_deg,
        ),
    )
    ipp_artifacts = export_ipp_points(
        ipp_points,
        output_dir=output_root / "ipp_points",
        prefix=ringo_csv_path.stem,
    )
    tec_grid = build_tec_grid(
        ipp_points,
        GridProcessingConfig(
            time_step=args.time_step,
            lat_resolution_deg=args.lat_resolution_deg,
            lon_resolution_deg=args.lon_resolution_deg,
        ),
    )
    tec_grid_artifacts = export_tec_grid(
        tec_grid,
        output_dir=output_root / "tec_grid",
        prefix=ringo_csv_path.stem,
    )
    anomaly_grid = build_anomaly_grid(
        tec_grid,
        AnomalyProcessingConfig(std_floor_tecu=args.std_floor_tecu),
    )
    anomaly_artifacts = export_anomaly_grid(
        anomaly_grid,
        output_dir=output_root / "anomaly_grid",
        prefix=ringo_csv_path.stem,
    )

    print(f"station_id={station_id}")
    print(f"stec_arcs={stec_artifacts.output_path}")
    print(f"station={station_artifacts.output_path}")
    print(f"ipp_points={ipp_artifacts.output_path}")
    print(f"tec_grid={tec_grid_artifacts.output_path}")
    print(f"anomaly_grid={anomaly_artifacts.output_path}")


if __name__ == "__main__":
    main()
