from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class GridProcessingConfig:
    time_step: str = "15min"
    lat_resolution_deg: float = 0.5
    lon_resolution_deg: float = 0.5


@dataclass(frozen=True)
class GridArtifacts:
    output_path: Path


def load_ipp_points(path: str | Path) -> pd.DataFrame:
    frame = pd.read_parquet(path).copy()
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    for column in ["ipp_lat_deg", "ipp_lon_deg", "vtec_tecu", "stec_leveled_tecu", "mapping_function"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _grid_center(values: pd.Series, resolution_deg: float) -> pd.Series:
    return np.floor(values / resolution_deg) * resolution_deg + (resolution_deg / 2.0)


def build_tec_grid(ipp_points: pd.DataFrame, config: GridProcessingConfig) -> pd.DataFrame:
    frame = ipp_points.copy()
    frame["time_bin"] = frame["time"].dt.floor(config.time_step)
    frame["grid_lat_deg"] = _grid_center(frame["ipp_lat_deg"], config.lat_resolution_deg)
    frame["grid_lon_deg"] = _grid_center(frame["ipp_lon_deg"], config.lon_resolution_deg)

    grouped = frame.groupby(["time_bin", "grid_lat_deg", "grid_lon_deg"], sort=True)
    grid = grouped.agg(
        sample_count=("vtec_tecu", "size"),
        mean_vtec_tecu=("vtec_tecu", "mean"),
        median_vtec_tecu=("vtec_tecu", "median"),
        std_vtec_tecu=("vtec_tecu", "std"),
        min_vtec_tecu=("vtec_tecu", "min"),
        max_vtec_tecu=("vtec_tecu", "max"),
        mean_stec_tecu=("stec_leveled_tecu", "mean"),
    ).reset_index()
    grid["std_vtec_tecu"] = grid["std_vtec_tecu"].fillna(0.0)
    return grid


def export_tec_grid(
    frame: pd.DataFrame,
    *,
    output_dir: str | Path,
    prefix: str,
) -> GridArtifacts:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{prefix}.tec_grid.parquet"
    frame.to_parquet(output_path, index=False)
    return GridArtifacts(output_path=output_path)
