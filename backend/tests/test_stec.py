from __future__ import annotations

import math

import pandas as pd

from app.processing.stec import (
    GPS_L1_WAVELENGTH_M,
    GPS_L2_WAVELENGTH_M,
    GPS_STEC_COEFFICIENT,
    StecProcessingConfig,
    build_stec_arcs,
    compute_geometry_free_and_stec,
)


def test_compute_geometry_free_and_stec_known_values() -> None:
    frame = pd.DataFrame(
        [
            {
                "station_id": "0001",
                "system": "G",
                "sat_id": "G01",
                "time": pd.Timestamp("2026-05-20T00:00:00Z"),
                "L1_value": 1.0,
                "L2_value": 1.0,
                "C1_value": 10.0,
                "C2_value": 12.0,
            }
        ]
    )
    processed = compute_geometry_free_and_stec(frame)
    expected_phase_gf = GPS_L1_WAVELENGTH_M - GPS_L2_WAVELENGTH_M
    expected_code_gf = 2.0
    assert math.isclose(processed.iloc[0]["phase_geometry_free_m"], expected_phase_gf, rel_tol=1e-12)
    assert math.isclose(processed.iloc[0]["code_geometry_free_m"], expected_code_gf, rel_tol=1e-12)
    assert math.isclose(processed.iloc[0]["phase_stec_tecu"], GPS_STEC_COEFFICIENT * expected_phase_gf, rel_tol=1e-12)
    assert math.isclose(processed.iloc[0]["code_stec_tecu"], GPS_STEC_COEFFICIENT * expected_code_gf, rel_tol=1e-12)


def test_build_stec_arcs_levels_phase_series_to_code_bias() -> None:
    rows = []
    for idx in range(12):
        rows.append(
            {
                "station_id": "0001",
                "system": "G",
                "sat_id": "G01",
                "time": pd.Timestamp("2026-05-20T00:00:00Z") + pd.Timedelta(seconds=30 * idx),
                "source_path": "synthetic",
                "az": 180.0,
                "el": 80.0,
                "L1_value": 100_000_000.0 + idx,
                "L2_value": 80_000_000.0 + idx,
                "C1_value": 20_000_000.0,
                "C2_value": 20_000_005.0,
                "S1_value": 50.0,
                "S2_value": 45.0,
            }
        )
    selected = pd.DataFrame(rows)
    result = build_stec_arcs(selected, StecProcessingConfig(gap_seconds=300, phase_jump_threshold_tecu=9999, min_arc_points=10))
    assert len(result) == 12
    assert result["arc_id"].nunique() == 1
    expected_bias = (result["code_stec_tecu"] - result["phase_stec_tecu"]).median()
    assert math.isclose(result.iloc[0]["arc_bias_tecu"], expected_bias, rel_tol=1e-12)
    assert math.isclose(
        result.iloc[0]["stec_leveled_tecu"],
        result.iloc[0]["phase_stec_tecu"] + expected_bias,
        rel_tol=1e-12,
    )

