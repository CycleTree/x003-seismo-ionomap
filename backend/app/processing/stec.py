from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


SPEED_OF_LIGHT_MPS = 299_792_458.0
GPS_L1_HZ = 1_575_420_000.0
GPS_L2_HZ = 1_227_600_000.0
GPS_L1_WAVELENGTH_M = SPEED_OF_LIGHT_MPS / GPS_L1_HZ
GPS_L2_WAVELENGTH_M = SPEED_OF_LIGHT_MPS / GPS_L2_HZ
TECU_SCALE = 40.3e16
GPS_STEC_COEFFICIENT = (GPS_L1_HZ**2 * GPS_L2_HZ**2) / (
    TECU_SCALE * (GPS_L1_HZ**2 - GPS_L2_HZ**2)
)


@dataclass(frozen=True)
class StecProcessingConfig:
    gap_seconds: float = 300.0
    phase_jump_threshold_tecu: float = 2.0
    min_arc_points: int = 10


@dataclass(frozen=True)
class StecArtifacts:
    output_path: Path


def load_selected_observations(path: str | Path) -> pd.DataFrame:
    frame = pd.read_parquet(path).copy()
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    for column in ["L1_value", "L2_value", "C1_value", "C2_value", "S1_value", "S2_value"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def load_stec_arcs(path: str | Path) -> pd.DataFrame:
    frame = pd.read_parquet(path).copy()
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    for column in [
        "az",
        "el",
        "phase_geometry_free_m",
        "code_geometry_free_m",
        "phase_stec_tecu",
        "code_stec_tecu",
        "gap_seconds",
        "phase_stec_diff_tecu",
        "arc_bias_tecu",
        "stec_leveled_tecu",
    ]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def prepare_dual_frequency_observations(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.loc[
        (frame["system"] == "G")
        & frame["L1_value"].notna()
        & frame["L2_value"].notna()
        & frame["C1_value"].notna()
        & frame["C2_value"].notna()
    ].copy()
    prepared = prepared.sort_values(["station_id", "sat_id", "time"]).reset_index(drop=True)
    return prepared


def compute_geometry_free_and_stec(frame: pd.DataFrame) -> pd.DataFrame:
    processed = frame.copy()
    processed["phase_geometry_free_m"] = (
        GPS_L1_WAVELENGTH_M * processed["L1_value"]
        - GPS_L2_WAVELENGTH_M * processed["L2_value"]
    )
    processed["code_geometry_free_m"] = processed["C2_value"] - processed["C1_value"]
    processed["phase_stec_tecu"] = GPS_STEC_COEFFICIENT * processed["phase_geometry_free_m"]
    processed["code_stec_tecu"] = GPS_STEC_COEFFICIENT * processed["code_geometry_free_m"]
    return processed


def detect_cycle_slips_and_segment_arcs(
    frame: pd.DataFrame,
    config: StecProcessingConfig,
) -> pd.DataFrame:
    processed = frame.copy()
    grouped = processed.groupby(["station_id", "sat_id"], sort=False)
    processed["gap_seconds"] = grouped["time"].diff().dt.total_seconds()
    processed["phase_stec_diff_tecu"] = grouped["phase_stec_tecu"].diff()
    processed["is_gap_break"] = processed["gap_seconds"].gt(config.gap_seconds).fillna(False)
    processed["is_phase_jump_break"] = (
        processed["phase_stec_diff_tecu"].abs().gt(config.phase_jump_threshold_tecu).fillna(False)
    )
    processed["is_arc_start"] = (
        grouped.cumcount().eq(0)
        | processed["is_gap_break"]
        | processed["is_phase_jump_break"]
    )
    processed["arc_index"] = (
        processed.groupby(["station_id", "sat_id"], sort=False)["is_arc_start"]
        .cumsum()
        .astype(int)
        - 1
    )
    processed["arc_id"] = (
        processed["station_id"]
        + ":"
        + processed["sat_id"]
        + ":"
        + processed["arc_index"].astype(str)
    )
    return processed


def level_phase_stec_by_arc(
    frame: pd.DataFrame,
    config: StecProcessingConfig,
) -> pd.DataFrame:
    processed = frame.copy()
    processed["arc_point_count"] = processed.groupby("arc_id", sort=False)["time"].transform("size")
    processed = processed.loc[processed["arc_point_count"] >= config.min_arc_points].copy()
    processed["arc_bias_tecu"] = processed.groupby("arc_id", sort=False).apply(
        lambda group: (group["code_stec_tecu"] - group["phase_stec_tecu"]).median()
    ).reindex(processed["arc_id"]).to_numpy()
    processed["stec_leveled_tecu"] = processed["phase_stec_tecu"] + processed["arc_bias_tecu"]
    return processed.reset_index(drop=True)


def build_stec_arcs(
    selected: pd.DataFrame,
    config: StecProcessingConfig,
) -> pd.DataFrame:
    prepared = prepare_dual_frequency_observations(selected)
    computed = compute_geometry_free_and_stec(prepared)
    segmented = detect_cycle_slips_and_segment_arcs(computed, config)
    leveled = level_phase_stec_by_arc(segmented, config)
    return leveled


def export_stec_arcs(
    frame: pd.DataFrame,
    *,
    output_dir: str | Path,
    prefix: str,
) -> StecArtifacts:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{prefix}.stec_arcs.parquet"
    frame.to_parquet(output_path, index=False)
    return StecArtifacts(output_path=output_path)
