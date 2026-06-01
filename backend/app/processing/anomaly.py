from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AnomalyProcessingConfig:
    std_floor_tecu: float = 0.1
    local_time_offset_hours: float = 9.0
    fallback_to_self_baseline: bool = True


@dataclass(frozen=True)
class AnomalyArtifacts:
    output_path: Path


def load_tec_grid(path: str | Path) -> pd.DataFrame:
    frame = pd.read_parquet(path).copy()
    frame["time_bin"] = pd.to_datetime(frame["time_bin"], utc=True)
    return frame


def load_baseline_tec_grids(paths: list[str | Path]) -> pd.DataFrame:
    frames = [load_tec_grid(path) for path in paths]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _with_local_time_slot(frame: pd.DataFrame, local_time_offset_hours: float) -> pd.DataFrame:
    enriched = frame.copy()
    local_time = enriched["time_bin"] + pd.to_timedelta(local_time_offset_hours, unit="h")
    enriched["local_time_slot"] = local_time.dt.strftime("%H:%M")
    return enriched


def _build_self_baseline(frame: pd.DataFrame, config: AnomalyProcessingConfig) -> pd.DataFrame:
    baseline = frame.copy()
    by_cell = baseline.groupby(["grid_lat_deg", "grid_lon_deg"], sort=False)
    baseline["baseline_vtec_tecu"] = by_cell["median_vtec_tecu"].transform("median")
    baseline["baseline_std_tecu"] = by_cell["median_vtec_tecu"].transform("std").fillna(0.0)
    baseline["baseline_reference_count"] = by_cell["median_vtec_tecu"].transform("count").astype(int)
    baseline["baseline_mode"] = "self"
    return baseline


def _build_quiet_day_lookup(reference_grid: pd.DataFrame, config: AnomalyProcessingConfig) -> pd.DataFrame:
    baseline = _with_local_time_slot(reference_grid, config.local_time_offset_hours)
    grouped = baseline.groupby(["grid_lat_deg", "grid_lon_deg", "local_time_slot"], sort=False)
    quiet = grouped["median_vtec_tecu"].agg(
        baseline_vtec_tecu="median",
        baseline_std_tecu="std",
        baseline_reference_count="count",
    ).reset_index()
    quiet["baseline_mode"] = "quiet_day"
    return quiet


def build_anomaly_grid(
    grid: pd.DataFrame,
    config: AnomalyProcessingConfig,
    baseline_grid: pd.DataFrame | None = None,
) -> pd.DataFrame:
    frame = grid.copy()
    frame["time_bin"] = pd.to_datetime(frame["time_bin"], utc=True)
    frame = _with_local_time_slot(frame, config.local_time_offset_hours)

    quiet_lookup = pd.DataFrame()
    if baseline_grid is not None and not baseline_grid.empty:
        quiet_lookup = _build_quiet_day_lookup(baseline_grid, config)

    if not quiet_lookup.empty:
        frame = frame.merge(
            quiet_lookup,
            on=["grid_lat_deg", "grid_lon_deg", "local_time_slot"],
            how="left",
        )
    else:
        frame["baseline_vtec_tecu"] = np.nan
        frame["baseline_std_tecu"] = np.nan
        frame["baseline_reference_count"] = 0
        frame["baseline_mode"] = pd.NA

    if config.fallback_to_self_baseline:
        self_baseline = _build_self_baseline(frame, config)
        frame["baseline_vtec_tecu"] = frame["baseline_vtec_tecu"].combine_first(self_baseline["baseline_vtec_tecu"])
        frame["baseline_std_tecu"] = frame["baseline_std_tecu"].combine_first(self_baseline["baseline_std_tecu"])
        frame["baseline_reference_count"] = frame["baseline_reference_count"].combine_first(
            self_baseline["baseline_reference_count"]
        )
        frame["baseline_mode"] = frame["baseline_mode"].combine_first(self_baseline["baseline_mode"])

    frame["baseline_std_tecu"] = pd.to_numeric(frame["baseline_std_tecu"], errors="coerce").fillna(0.0)
    frame["baseline_std_tecu"] = frame["baseline_std_tecu"].clip(lower=config.std_floor_tecu)
    frame["baseline_reference_count"] = (
        pd.to_numeric(frame["baseline_reference_count"], errors="coerce").fillna(0).astype(int)
    )
    frame["baseline_mode"] = frame["baseline_mode"].fillna("self")
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
