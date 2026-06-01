from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, csr_matrix, vstack
from scipy.sparse.linalg import lsqr


@dataclass(frozen=True)
class RegionalVtecConfig:
    time_step: str = "15min"
    lat_resolution_deg: float = 0.5
    lon_resolution_deg: float = 0.5
    lat_min_deg: float = 20.0
    lat_max_deg: float = 50.0
    lon_min_deg: float = 120.0
    lon_max_deg: float = 155.0
    smoothing_lambda: float = 0.25
    padding_cells: int = 1


@dataclass(frozen=True)
class RegionalVtecArtifacts:
    output_path: Path


def load_ipp_points(path: str | Path) -> pd.DataFrame:
    frame = pd.read_parquet(path).copy()
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    for column in ["ipp_lat_deg", "ipp_lon_deg", "vtec_tecu", "stec_leveled_tecu", "mapping_function"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _axis_centers(min_deg: float, max_deg: float, resolution_deg: float) -> np.ndarray:
    count = int(round((max_deg - min_deg) / resolution_deg))
    return min_deg + (np.arange(count) + 0.5) * resolution_deg


def _grid_index(lat_idx: int, lon_idx: int, lon_count: int) -> int:
    return lat_idx * lon_count + lon_idx


def _local_grid_window(
    frame: pd.DataFrame,
    config: RegionalVtecConfig,
    global_lat_count: int,
    global_lon_count: int,
) -> tuple[int, int, int, int]:
    lat_positions = (frame["ipp_lat_deg"].to_numpy(dtype=float) - config.lat_min_deg) / config.lat_resolution_deg
    lon_positions = (frame["ipp_lon_deg"].to_numpy(dtype=float) - config.lon_min_deg) / config.lon_resolution_deg

    min_lat_idx = max(0, int(np.floor(np.nanmin(lat_positions))) - config.padding_cells)
    max_lat_idx = min(global_lat_count - 1, int(np.floor(np.nanmax(lat_positions))) + config.padding_cells + 1)
    min_lon_idx = max(0, int(np.floor(np.nanmin(lon_positions))) - config.padding_cells)
    max_lon_idx = min(global_lon_count - 1, int(np.floor(np.nanmax(lon_positions))) + config.padding_cells + 1)
    return min_lat_idx, max_lat_idx, min_lon_idx, max_lon_idx


def _build_smoothing_matrix(lat_count: int, lon_count: int, smoothing_lambda: float) -> csr_matrix:
    if smoothing_lambda <= 0:
        return csr_matrix((0, lat_count * lon_count), dtype=float)

    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    row_idx = 0
    weight = np.sqrt(smoothing_lambda)

    for lat_idx in range(lat_count):
        for lon_idx in range(lon_count):
            current = _grid_index(lat_idx, lon_idx, lon_count)
            if lon_idx + 1 < lon_count:
                right = _grid_index(lat_idx, lon_idx + 1, lon_count)
                rows.extend([row_idx, row_idx])
                cols.extend([current, right])
                data.extend([weight, -weight])
                row_idx += 1
            if lat_idx + 1 < lat_count:
                down = _grid_index(lat_idx + 1, lon_idx, lon_count)
                rows.extend([row_idx, row_idx])
                cols.extend([current, down])
                data.extend([weight, -weight])
                row_idx += 1

    return coo_matrix((data, (rows, cols)), shape=(row_idx, lat_count * lon_count)).tocsr()


def _observation_matrix(
    frame: pd.DataFrame,
    lat_offset: int,
    lon_offset: int,
    lat_count: int,
    lon_count: int,
    config: RegionalVtecConfig,
) -> tuple[csr_matrix, np.ndarray]:
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    valid_obs_indices: list[int] = []

    for obs_idx, row in enumerate(frame.itertuples(index=False)):
        lat = float(row.ipp_lat_deg)
        lon = float(row.ipp_lon_deg)
        if not (config.lat_min_deg <= lat <= config.lat_max_deg and config.lon_min_deg <= lon <= config.lon_max_deg):
            continue

        lat_pos = (lat - config.lat_min_deg) / config.lat_resolution_deg - lat_offset
        lon_pos = (lon - config.lon_min_deg) / config.lon_resolution_deg - lon_offset
        base_lat = int(np.floor(lat_pos))
        base_lon = int(np.floor(lon_pos))
        frac_lat = lat_pos - base_lat
        frac_lon = lon_pos - base_lon

        base_lat = min(max(base_lat, 0), lat_count - 1)
        base_lon = min(max(base_lon, 0), lon_count - 1)
        next_lat = min(base_lat + 1, lat_count - 1)
        next_lon = min(base_lon + 1, lon_count - 1)

        weights = [
            ((1.0 - frac_lat) * (1.0 - frac_lon), base_lat, base_lon),
            ((1.0 - frac_lat) * frac_lon, base_lat, next_lon),
            (frac_lat * (1.0 - frac_lon), next_lat, base_lon),
            (frac_lat * frac_lon, next_lat, next_lon),
        ]

        seen: dict[int, float] = {}
        for weight, lat_idx, lon_idx in weights:
            if weight <= 0:
                continue
            cell_idx = _grid_index(lat_idx, lon_idx, lon_count)
            seen[cell_idx] = seen.get(cell_idx, 0.0) + float(weight)

        if not seen:
            continue

        out_row = len(valid_obs_indices)
        valid_obs_indices.append(obs_idx)
        for cell_idx, weight in seen.items():
            rows.append(out_row)
            cols.append(cell_idx)
            data.append(weight)

    matrix = coo_matrix((data, (rows, cols)), shape=(len(valid_obs_indices), lat_count * lon_count)).tocsr()
    return matrix, np.array(valid_obs_indices, dtype=int)


def _solve_time_bin(
    frame: pd.DataFrame,
    global_lat_centers: np.ndarray,
    global_lon_centers: np.ndarray,
    config: RegionalVtecConfig,
) -> pd.DataFrame:
    lat_start, lat_end, lon_start, lon_end = _local_grid_window(
        frame, config, len(global_lat_centers), len(global_lon_centers)
    )
    lat_centers = global_lat_centers[lat_start : lat_end + 1]
    lon_centers = global_lon_centers[lon_start : lon_end + 1]
    local_lat_count = len(lat_centers)
    local_lon_count = len(lon_centers)
    observation_matrix, valid_indices = _observation_matrix(
        frame,
        lat_start,
        lon_start,
        local_lat_count,
        local_lon_count,
        config,
    )
    if observation_matrix.shape[0] == 0:
        return pd.DataFrame(columns=["time_bin", "grid_lat_deg", "grid_lon_deg", "sample_count", "mean_vtec_tecu", "median_vtec_tecu", "std_vtec_tecu", "min_vtec_tecu", "max_vtec_tecu", "mean_stec_tecu"])

    observed = frame.iloc[valid_indices].reset_index(drop=True)
    target = observed["vtec_tecu"].to_numpy(dtype=float)
    smoothing_matrix = _build_smoothing_matrix(local_lat_count, local_lon_count, config.smoothing_lambda)
    system_matrix = vstack([observation_matrix, smoothing_matrix], format="csr")
    system_target = np.concatenate([target, np.zeros(smoothing_matrix.shape[0], dtype=float)])
    solved = lsqr(system_matrix, system_target, atol=1e-8, btol=1e-8, iter_lim=500)[0]

    weighted_counts = np.asarray(observation_matrix.T @ np.ones(observation_matrix.shape[0], dtype=float)).reshape(-1)
    weighted_vtec = np.asarray(observation_matrix.T @ target).reshape(-1)
    weighted_stec = np.asarray(observation_matrix.T @ observed["stec_leveled_tecu"].to_numpy(dtype=float)).reshape(-1)
    weighted_sq_residual = np.asarray(
        observation_matrix.T @ ((target - observation_matrix @ solved) ** 2)
    ).reshape(-1)

    rows: list[dict[str, object]] = []
    time_bin = observed["time_bin"].iloc[0]
    for lat_idx, lat_center in enumerate(lat_centers):
        for lon_idx, lon_center in enumerate(lon_centers):
            cell_idx = _grid_index(lat_idx, lon_idx, local_lon_count)
            count = float(weighted_counts[cell_idx])
            sample_count = int(round(count))
            solved_vtec = float(solved[cell_idx])
            std_vtec = float(np.sqrt(weighted_sq_residual[cell_idx] / count)) if count > 0 else 0.0
            mean_stec = float(weighted_stec[cell_idx] / count) if count > 0 else np.nan
            rows.append(
                {
                    "time_bin": time_bin,
                    "grid_lat_deg": float(lat_center),
                    "grid_lon_deg": float(lon_center),
                    "sample_count": sample_count,
                    "mean_vtec_tecu": solved_vtec,
                    "median_vtec_tecu": solved_vtec,
                    "std_vtec_tecu": std_vtec,
                    "min_vtec_tecu": solved_vtec,
                    "max_vtec_tecu": solved_vtec,
                    "mean_stec_tecu": mean_stec,
                }
            )

    return pd.DataFrame(rows)


def build_regional_vtec_grid(ipp_points: pd.DataFrame, config: RegionalVtecConfig) -> pd.DataFrame:
    frame = ipp_points.copy()
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    frame = frame.loc[
        frame["ipp_lat_deg"].notna()
        & frame["ipp_lon_deg"].notna()
        & frame["vtec_tecu"].notna()
        & frame["stec_leveled_tecu"].notna()
    ].copy()
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "time_bin",
                "grid_lat_deg",
                "grid_lon_deg",
                "sample_count",
                "mean_vtec_tecu",
                "median_vtec_tecu",
                "std_vtec_tecu",
                "min_vtec_tecu",
                "max_vtec_tecu",
                "mean_stec_tecu",
            ]
        )

    frame["time_bin"] = frame["time"].dt.floor(config.time_step)
    lat_centers = _axis_centers(config.lat_min_deg, config.lat_max_deg, config.lat_resolution_deg)
    lon_centers = _axis_centers(config.lon_min_deg, config.lon_max_deg, config.lon_resolution_deg)
    bins: list[pd.DataFrame] = []
    for _, time_frame in frame.groupby("time_bin", sort=True):
        bins.append(_solve_time_bin(time_frame.reset_index(drop=True), lat_centers, lon_centers, config))
    return pd.concat(bins, ignore_index=True) if bins else pd.DataFrame()


def export_regional_vtec_grid(
    frame: pd.DataFrame,
    *,
    output_dir: str | Path,
    prefix: str,
) -> RegionalVtecArtifacts:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{prefix}.tec_grid.parquet"
    frame.to_parquet(output_path, index=False)
    return RegionalVtecArtifacts(output_path=output_path)
