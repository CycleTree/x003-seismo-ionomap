from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import os
import subprocess

import pandas as pd

from app.config.gnss import IngestConfig
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


@dataclass(frozen=True)
class StationPair:
    station_code: str
    obs_path: Path
    nav_path: Path

    @property
    def stem(self) -> str:
        return self.obs_path.name.replace(".26d.gz", "")


@dataclass(frozen=True)
class StationProcessingConfig:
    output_root: Path
    gap_seconds: float
    phase_jump_threshold_tecu: float
    min_arc_points: int
    shell_height_km: float
    min_elevation_deg: float


def collect_station_pairs(raw_dir: str | Path) -> list[StationPair]:
    raw_dir = Path(raw_dir)
    obs_files = sorted(raw_dir.glob("*.26d.gz"))
    nav_map = {path.name.replace(".26N.tar.gz", ""): path for path in raw_dir.glob("*.26N.tar.gz")}
    pairs: list[StationPair] = []
    for obs_path in obs_files:
        stem = obs_path.name.replace(".26d.gz", "")
        nav_path = nav_map.get(stem)
        if nav_path is None:
            continue
        pairs.append(StationPair(station_code=obs_path.name[:4], obs_path=obs_path, nav_path=nav_path))
    return pairs


def ensure_output_directories(output_root: Path) -> None:
    for name in [
        "qc",
        "ringo_csv",
        "observations",
        "stec_arcs",
        "stations",
        "ipp_points",
        "national",
        "tec_grid",
        "anomaly_grid",
    ]:
        (output_root / name).mkdir(parents=True, exist_ok=True)


def run_ringo_qc_and_csv(pair: StationPair, output_root: Path) -> tuple[Path, Path]:
    qc_path = output_root / "qc" / f"{pair.stem}.qc.log"
    csv_path = output_root / "ringo_csv" / f"{pair.stem}_nav.csv"
    subprocess.run(
        ["ringo", "qc", str(pair.obs_path), str(pair.nav_path), "-o", str(qc_path)],
        check=True,
    )
    subprocess.run(
        ["ringo", "rnxcsv", str(pair.obs_path), str(pair.nav_path), "-o", str(csv_path)],
        check=True,
    )
    return qc_path, csv_path


def process_single_station(pair: StationPair, config: StationProcessingConfig) -> Path:
    ensure_output_directories(config.output_root)
    qc_path, csv_path = run_ringo_qc_and_csv(pair, config.output_root)

    station_metadata_dict = parse_qc_summary(qc_path)
    station_id = str(station_metadata_dict.get("station_id") or pair.station_code)
    station_metadata_dict["station_id"] = station_id

    ringo_frame = load_ringo_csv(csv_path)
    wide = normalize_wide_observations(ringo_frame, station_id=station_id, source_path=csv_path)
    long_frame = wide_to_long_observations(wide)
    selected = select_priority_observations(wide, IngestConfig().observation_priority)
    export_observation_products(
        wide=wide,
        long_frame=long_frame,
        selected=selected,
        output_dir=config.output_root / "observations",
        prefix=pair.stem,
    )

    stec_arcs = build_stec_arcs(
        selected,
        StecProcessingConfig(
            gap_seconds=config.gap_seconds,
            phase_jump_threshold_tecu=config.phase_jump_threshold_tecu,
            min_arc_points=config.min_arc_points,
        ),
    )
    export_stec_arcs(stec_arcs, output_dir=config.output_root / "stec_arcs", prefix=pair.stem)

    station_artifacts = export_station_metadata(
        station_metadata_dict,
        output_dir=config.output_root / "stations",
        prefix=station_id,
    )
    station_metadata = load_station_metadata(station_artifacts.output_path)
    ipp_points = build_ipp_points(
        stec_arcs,
        station_metadata,
        IppProcessingConfig(
            shell_height_km=config.shell_height_km,
            min_elevation_deg=config.min_elevation_deg,
        ),
    )
    ipp_artifacts = export_ipp_points(
        ipp_points,
        output_dir=config.output_root / "ipp_points",
        prefix=pair.stem,
    )
    return ipp_artifacts.output_path


def run_station_batch(
    pairs: list[StationPair],
    config: StationProcessingConfig,
    *,
    max_workers: int | None = None,
) -> list[Path]:
    if max_workers is None:
        max_workers = max(1, min(os.cpu_count() or 1, 8))
    results: list[Path] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_station, pair, config): pair
            for pair in pairs
        }
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results)


def merge_ipp_point_files(ipp_paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_parquet(path) for path in ipp_paths]
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True)
    merged["time"] = pd.to_datetime(merged["time"], utc=True)
    return merged
