from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BiasProcessingConfig:
    receiver_penalty: float = 0.01
    satellite_penalty: float = 0.01
    arc_penalty: float = 1.0


@dataclass(frozen=True)
class BiasEstimationResult:
    receiver_biases: pd.DataFrame
    satellite_biases: pd.DataFrame
    arc_biases: pd.DataFrame


def _build_design_matrix(
    frame: pd.DataFrame,
    station_ids: list[str],
    sat_ids: list[str],
    arc_ids: list[str],
) -> np.ndarray:
    num_rows = len(frame)
    num_cols = len(station_ids) + len(sat_ids) + len(arc_ids)
    matrix = np.zeros((num_rows, num_cols), dtype=float)

    station_index = {value: idx for idx, value in enumerate(station_ids)}
    sat_index = {value: idx for idx, value in enumerate(sat_ids)}
    arc_index = {value: idx for idx, value in enumerate(arc_ids)}
    sat_offset = len(station_ids)
    arc_offset = sat_offset + len(sat_ids)

    for row_idx, row in enumerate(frame.itertuples(index=False)):
        matrix[row_idx, station_index[row.station_id]] = 1.0
        matrix[row_idx, sat_offset + sat_index[row.sat_id]] = 1.0
        matrix[row_idx, arc_offset + arc_index[row.arc_id]] = 1.0

    return matrix


def estimate_bias_components(
    frame: pd.DataFrame,
    config: BiasProcessingConfig,
) -> BiasEstimationResult:
    bias_frame = frame.loc[
        frame["code_stec_tecu"].notna()
        & frame["phase_stec_tecu"].notna()
        & frame["arc_id"].notna()
    ].copy()
    if bias_frame.empty:
        return BiasEstimationResult(
            receiver_biases=pd.DataFrame(columns=["station_id", "receiver_bias_tecu"]),
            satellite_biases=pd.DataFrame(columns=["sat_id", "satellite_bias_tecu"]),
            arc_biases=pd.DataFrame(columns=["arc_id", "arc_bias_tecu"]),
        )

    bias_frame["bias_observation_tecu"] = bias_frame["code_stec_tecu"] - bias_frame["phase_stec_tecu"]
    station_ids = sorted(bias_frame["station_id"].astype(str).unique().tolist())
    sat_ids = sorted(bias_frame["sat_id"].astype(str).unique().tolist())
    arc_ids = sorted(bias_frame["arc_id"].astype(str).unique().tolist())

    design = _build_design_matrix(bias_frame, station_ids, sat_ids, arc_ids)
    target = bias_frame["bias_observation_tecu"].to_numpy(dtype=float)

    penalties = np.concatenate(
        [
            np.full(len(station_ids), config.receiver_penalty, dtype=float),
            np.full(len(sat_ids), config.satellite_penalty, dtype=float),
            np.full(len(arc_ids), config.arc_penalty, dtype=float),
        ]
    )
    regularization = np.diag(np.sqrt(penalties))
    augmented_design = np.vstack([design, regularization])
    augmented_target = np.concatenate([target, np.zeros(len(penalties), dtype=float)])
    coefficients, *_ = np.linalg.lstsq(augmented_design, augmented_target, rcond=None)

    receiver_biases = coefficients[: len(station_ids)]
    satellite_biases = coefficients[len(station_ids) : len(station_ids) + len(sat_ids)]
    arc_biases = coefficients[len(station_ids) + len(sat_ids) :]

    receiver_mean = receiver_biases.mean() if len(receiver_biases) else 0.0
    satellite_mean = satellite_biases.mean() if len(satellite_biases) else 0.0
    receiver_biases = receiver_biases - receiver_mean
    satellite_biases = satellite_biases - satellite_mean
    arc_biases = arc_biases + receiver_mean + satellite_mean

    receiver_map = dict(zip(station_ids, receiver_biases))
    satellite_map = dict(zip(sat_ids, satellite_biases))
    shared_bias = (
        bias_frame["station_id"].map(receiver_map).to_numpy(dtype=float)
        + bias_frame["sat_id"].map(satellite_map).to_numpy(dtype=float)
    )
    arc_bias_lookup = (
        bias_frame.assign(shared_bias_tecu=shared_bias)
        .groupby("arc_id", sort=False)
        .apply(lambda group: (group["bias_observation_tecu"] - group["shared_bias_tecu"]).median())
    )
    arc_biases = np.array([arc_bias_lookup[arc_id] for arc_id in arc_ids], dtype=float)

    return BiasEstimationResult(
        receiver_biases=pd.DataFrame(
            {"station_id": station_ids, "receiver_bias_tecu": receiver_biases}
        ),
        satellite_biases=pd.DataFrame(
            {"sat_id": sat_ids, "satellite_bias_tecu": satellite_biases}
        ),
        arc_biases=pd.DataFrame(
            {"arc_id": arc_ids, "arc_bias_tecu": arc_biases}
        ),
    )


def apply_bias_components(
    frame: pd.DataFrame,
    biases: BiasEstimationResult,
) -> pd.DataFrame:
    processed = frame.copy()
    processed = processed.merge(biases.receiver_biases, on="station_id", how="left")
    processed = processed.merge(biases.satellite_biases, on="sat_id", how="left")
    processed = processed.merge(biases.arc_biases, on="arc_id", how="left")
    for column in ["receiver_bias_tecu", "satellite_bias_tecu", "arc_bias_tecu"]:
        processed[column] = pd.to_numeric(processed[column], errors="coerce").fillna(0.0)
    processed["stec_leveled_tecu"] = (
        processed["phase_stec_tecu"]
        + processed["receiver_bias_tecu"]
        + processed["satellite_bias_tecu"]
        + processed["arc_bias_tecu"]
    )
    processed["bias_model_residual_tecu"] = processed["code_stec_tecu"] - processed["stec_leveled_tecu"]
    return processed


def extract_bias_tables(frame: pd.DataFrame) -> BiasEstimationResult:
    return BiasEstimationResult(
        receiver_biases=frame[["station_id", "receiver_bias_tecu"]].drop_duplicates().reset_index(drop=True),
        satellite_biases=frame[["sat_id", "satellite_bias_tecu"]].drop_duplicates().reset_index(drop=True),
        arc_biases=frame[["arc_id", "arc_bias_tecu"]].drop_duplicates().reset_index(drop=True),
    )
