from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AnomalyProcessingConfig:
    std_floor_tecu: float = 0.1


@dataclass(frozen=True)
class AnomalyArtifacts:
    output_path: Path


def load_tec_grid(path: str | Path) -> pd.DataFrame:
    frame = pd.read_parquet(path).copy()
    frame["time_bin"] = pd.to_datetime(frame["time_bin"], utc=True)
    return frame


def build_anomaly_grid(grid: pd.DataFrame, config: AnomalyProcessingConfig) -> pd.DataFrame:
    frame = grid.copy()
    by_cell = frame.groupby(["grid_lat_deg", "grid_lon_deg"], sort=False)
    frame["baseline_vtec_tecu"] = by_cell["median_vtec_tecu"].transform("median")
    frame["baseline_std_tecu"] = by_cell["median_vtec_tecu"].transform("std").fillna(0.0)
    frame["baseline_std_tecu"] = frame["baseline_std_tecu"].clip(lower=config.std_floor_tecu)
    frame["delta_vtec_tecu"] = frame["median_vtec_tecu"] - frame["baseline_vtec_tecu"]
    frame["z_score"] = frame["delta_vtec_tecu"] / frame["baseline_std_tecu"]

    frame = frame.sort_values(["grid_lat_deg", "grid_lon_deg", "time_bin"]).reset_index(drop=True)
    by_cell_sorted = frame.groupby(["grid_lat_deg", "grid_lon_deg"], sort=False)
    frame["delta_prev_step_tecu"] = by_cell_sorted["median_vtec_tecu"].diff()
    frame["abs_z_score"] = np.abs(frame["z_score"])
    return frame


def export_anomaly_grid(
    frame: pd.DataFrame,
    *,
    output_dir: str | Path,
    prefix: str,
) -> AnomalyArtifacts:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{prefix}.anomaly_grid.parquet"
    frame.to_parquet(output_path, index=False)
    return AnomalyArtifacts(output_path=output_path)
