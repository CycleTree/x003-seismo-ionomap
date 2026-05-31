from __future__ import annotations

import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config.gnss import IngestConfig
from app.processing.ringo_ingest import (
    export_observation_products,
    load_ringo_csv,
    normalize_wide_observations,
    select_priority_observations,
    wide_to_long_observations,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest RINGO rnxcsv output into Parquet artifacts.")
    parser.add_argument("input_csv", help="Path to rnxcsv CSV file")
    parser.add_argument(
        "--output-dir",
        default="data/intermediate/observations",
        help="Directory for generated Parquet files",
    )
    parser.add_argument(
        "--station-id",
        default=None,
        help="Station identifier override. Defaults to the CSV stem prefix.",
    )
    return parser


def derive_station_id(path: Path, explicit_station_id: str | None, config: IngestConfig) -> str:
    if explicit_station_id:
        return explicit_station_id
    if config.default_station_id:
        return config.default_station_id
    return path.stem.split(".")[0]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = IngestConfig()
    input_csv = Path(args.input_csv)
    station_id = derive_station_id(input_csv, args.station_id, config)

    frame = load_ringo_csv(input_csv)
    wide = normalize_wide_observations(frame, station_id=station_id, source_path=input_csv)
    long_frame = wide_to_long_observations(wide)
    selected = select_priority_observations(wide, config.observation_priority)
    artifacts = export_observation_products(
        wide=wide,
        long_frame=long_frame,
        selected=selected,
        output_dir=args.output_dir,
        prefix=input_csv.stem,
    )

    print(f"station_id={station_id}")
    print(f"rows.wide={len(wide)}")
    print(f"rows.long={len(long_frame)}")
    print(f"rows.selected={len(selected)}")
    print(f"wide={artifacts.wide_path}")
    print(f"long={artifacts.long_path}")
    print(f"selected={artifacts.selected_path}")


if __name__ == "__main__":
    main()
