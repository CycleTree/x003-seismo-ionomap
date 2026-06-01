from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class IppProcessingConfig:
    shell_height_km: float = 350.0
    min_elevation_deg: float = 15.0


@dataclass(frozen=True)
class IppArtifacts:
    output_path: Path


def load_station_metadata(path: str | Path) -> pd.DataFrame:
    frame = pd.read_parquet(path).copy()
    return frame


def attach_station_metadata(
    stec_arcs: pd.DataFrame,
    station_metadata: pd.DataFrame,
) -> pd.DataFrame:
    columns = ["station_id", "lat_deg", "lon_deg", "height_m", "x_m", "y_m", "z_m"]
    joined = stec_arcs.merge(station_metadata[columns], on="station_id", how="left", validate="many_to_one")
    if joined["lat_deg"].isna().any():
        raise ValueError("Station metadata missing for one or more stec arc rows")
    return joined


def apply_elevation_mask(frame: pd.DataFrame, min_elevation_deg: float) -> pd.DataFrame:
    if "el" not in frame.columns:
        raise ValueError("Elevation column 'el' is required for IPP computation")
    return frame.loc[frame["el"].ge(min_elevation_deg)].copy()


def compute_mapping_function(el_rad: np.ndarray, shell_height_km: float) -> np.ndarray:
    ratio = EARTH_RADIUS_KM * np.cos(el_rad) / (EARTH_RADIUS_KM + shell_height_km)
    return 1.0 / np.sqrt(1.0 - ratio**2)


def compute_earth_central_angle(el_rad: np.ndarray, shell_height_km: float) -> np.ndarray:
    ratio = EARTH_RADIUS_KM * np.cos(el_rad) / (EARTH_RADIUS_KM + shell_height_km)
    return (np.pi / 2.0) - el_rad - np.arcsin(ratio)


def compute_ipp_coordinates(frame: pd.DataFrame, shell_height_km: float) -> pd.DataFrame:
    processed = frame.copy()
    lat_rad = np.deg2rad(processed["lat_deg"].to_numpy())
    lon_rad = np.deg2rad(processed["lon_deg"].to_numpy())
    az_rad = np.deg2rad(processed["az"].to_numpy())
    el_rad = np.deg2rad(processed["el"].to_numpy())

    psi = compute_earth_central_angle(el_rad, shell_height_km)
    sin_ipp_lat = np.sin(lat_rad) * np.cos(psi) + np.cos(lat_rad) * np.sin(psi) * np.cos(az_rad)
    ipp_lat_rad = np.arcsin(np.clip(sin_ipp_lat, -1.0, 1.0))
    ipp_lon_rad = lon_rad + np.arctan2(
        np.sin(psi) * np.sin(az_rad),
        np.cos(lat_rad) * np.cos(psi) - np.sin(lat_rad) * np.sin(psi) * np.cos(az_rad),
    )

    mapping_function = compute_mapping_function(el_rad, shell_height_km)

    processed["shell_height_km"] = shell_height_km
    processed["mapping_function"] = mapping_function
    processed["vtec_tecu"] = processed["stec_leveled_tecu"] / mapping_function
    processed["ipp_lat_deg"] = np.rad2deg(ipp_lat_rad)
    processed["ipp_lon_deg"] = ((np.rad2deg(ipp_lon_rad) + 180.0) % 360.0) - 180.0
    return processed


def build_ipp_points(
    stec_arcs: pd.DataFrame,
    station_metadata: pd.DataFrame,
    config: IppProcessingConfig,
) -> pd.DataFrame:
    joined = attach_station_metadata(stec_arcs, station_metadata)
    masked = apply_elevation_mask(joined, config.min_elevation_deg)
    return compute_ipp_coordinates(masked, config.shell_height_km)


def export_ipp_points(
    frame: pd.DataFrame,
    *,
    output_dir: str | Path,
    prefix: str,
) -> IppArtifacts:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{prefix}.ipp_points.parquet"
    frame.to_parquet(output_path, index=False)
    return IppArtifacts(output_path=output_path)
