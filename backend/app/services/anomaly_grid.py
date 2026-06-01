from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

DisplayMode = str


@dataclass(frozen=True)
class AnomalyGridServiceConfig:
    root_dir: Path
    prefixes: tuple[str, ...] = ("national_make", "full_run_make")


def _grid_dirs(config: AnomalyGridServiceConfig) -> list[Path]:
    return [config.root_dir / prefix / "anomaly_grid" for prefix in config.prefixes]


def list_anomaly_grid_files(config: AnomalyGridServiceConfig) -> list[Path]:
    files: list[Path] = []
    for grid_dir in _grid_dirs(config):
        files.extend(sorted(grid_dir.glob("*.anomaly_grid.parquet")))
        if files:
            break
    return files


def load_anomaly_grid(config: AnomalyGridServiceConfig) -> pd.DataFrame:
    files = list_anomaly_grid_files(config)
    if not files:
        search_dirs = ", ".join(str(path) for path in _grid_dirs(config))
        raise FileNotFoundError(f"No anomaly grid parquet found in {search_dirs}")
    frame = pd.read_parquet(files[-1]).copy()
    frame["time_bin"] = pd.to_datetime(frame["time_bin"], utc=True)
    if "baseline_mode" not in frame.columns:
        frame["baseline_mode"] = "self"
    if "local_time_slot" not in frame.columns:
        frame["local_time_slot"] = frame["time_bin"].dt.strftime("%H:%M")
    return frame


def list_available_times(frame: pd.DataFrame) -> list[str]:
    return sorted(frame["time_bin"].dt.strftime("%Y-%m-%dT%H:%M:%SZ").unique().tolist())


def filter_grid_by_time(frame: pd.DataFrame, time_iso: str | None) -> tuple[pd.DataFrame, str]:
    if time_iso:
        target = pd.Timestamp(time_iso, tz="UTC")
    else:
        target = frame["time_bin"].max()
    filtered = frame.loc[frame["time_bin"] == target].copy()
    return filtered, target.strftime("%Y-%m-%dT%H:%M:%SZ")


def value_column_for_mode(mode: DisplayMode) -> str:
    if mode == "anomaly":
        return "z_score"
    if mode == "detrended":
        return "delta_vtec_tecu"
    if mode == "vtec":
        return "median_vtec_tecu"
    raise ValueError(f"Unsupported display mode: {mode}")


def stats_for_mode(frame: pd.DataFrame, mode: DisplayMode) -> dict[str, float | int]:
    value_column = value_column_for_mode(mode)
    values = frame[value_column].astype(float)
    return {
        "cellCount": int(len(frame)),
        "maxAbsValue": float(values.abs().max()),
        "meanValue": float(values.mean()),
    }


def anomaly_grid_to_geojson(
    frame: pd.DataFrame,
    *,
    mode: DisplayMode,
    lat_resolution_deg: float = 0.5,
    lon_resolution_deg: float = 0.5,
) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    half_lat = lat_resolution_deg / 2.0
    half_lon = lon_resolution_deg / 2.0
    value_column = value_column_for_mode(mode)
    for row in frame.itertuples(index=False):
        south = row.grid_lat_deg - half_lat
        north = row.grid_lat_deg + half_lat
        west = row.grid_lon_deg - half_lon
        east = row.grid_lon_deg + half_lon
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [west, south],
                            [east, south],
                            [east, north],
                            [west, north],
                            [west, south],
                        ]
                    ],
                },
                "properties": {
                    "time": row.time_bin.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "grid_lat_deg": row.grid_lat_deg,
                    "grid_lon_deg": row.grid_lon_deg,
                    "sample_count": int(row.sample_count),
                    "median_vtec_tecu": float(row.median_vtec_tecu),
                    "baseline_vtec_tecu": float(row.baseline_vtec_tecu),
                    "baseline_mode": str(row.baseline_mode),
                    "delta_vtec_tecu": float(row.delta_vtec_tecu),
                    "z_score": float(row.z_score),
                    "abs_z_score": float(row.abs_z_score),
                    "local_time_slot": str(row.local_time_slot),
                    "display_mode": mode,
                    "display_value": float(getattr(row, value_column)),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}
