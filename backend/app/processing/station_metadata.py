from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pymap3d as pm


APPROX_XYZ_PATTERN = re.compile(
    r"# Approx XYZ\s*:\s*([-+0-9.]+),\s*([-+0-9.]+),\s*([-+0-9.]+)"
)
MARKER_PATTERN = re.compile(r"# Marker\s*:\s*(\S+)")
RECEIVER_PATTERN = re.compile(r"# Receiver\s*:\s*(.+)")
ANTENNA_PATTERN = re.compile(r"# Antenna\s*:\s*(.+)")


@dataclass(frozen=True)
class StationMetadataArtifacts:
    output_path: Path


def parse_qc_summary(qc_path: str | Path) -> dict[str, object]:
    qc_path = Path(qc_path)
    text = qc_path.read_text()
    xyz_match = APPROX_XYZ_PATTERN.search(text)
    marker_match = MARKER_PATTERN.search(text)
    receiver_match = RECEIVER_PATTERN.search(text)
    antenna_match = ANTENNA_PATTERN.search(text)
    if xyz_match is None:
        raise ValueError(f"Approx XYZ not found in {qc_path}")
    x_m, y_m, z_m = (float(value) for value in xyz_match.groups())
    lat_deg, lon_deg, height_m = pm.ecef2geodetic(x_m, y_m, z_m)
    return {
        "station_id": marker_match.group(1) if marker_match else qc_path.stem,
        "receiver": receiver_match.group(1).strip() if receiver_match else None,
        "antenna": antenna_match.group(1).strip() if antenna_match else None,
        "x_m": x_m,
        "y_m": y_m,
        "z_m": z_m,
        "lat_deg": float(lat_deg),
        "lon_deg": float(lon_deg),
        "height_m": float(height_m),
        "source_path": str(qc_path),
    }


def export_station_metadata(
    metadata: dict[str, object],
    *,
    output_dir: str | Path,
    prefix: str,
) -> StationMetadataArtifacts:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{prefix}.station.parquet"
    pd.DataFrame([metadata]).to_parquet(output_path, index=False)
    return StationMetadataArtifacts(output_path=output_path)
