from __future__ import annotations

import pandas as pd

from app.processing.quality_control import QualityControlConfig, annotate_quality_flags, apply_quality_control


def test_apply_quality_control_filters_expected_rows() -> None:
    frame = pd.DataFrame(
        [
            {
                "station_id": "0001",
                "system": "G",
                "sat_id": "G01",
                "time": pd.Timestamp("2026-05-20T00:00:00Z"),
                "el": 30.0,
                "L1_value": 1.0,
                "L2_value": 2.0,
                "C1_value": 100.0,
                "C2_value": 104.0,
                "S1_value": 45.0,
                "S2_value": 42.0,
                "L1_lli": 0,
                "L2_lli": 0,
            },
            {
                "station_id": "0001",
                "system": "G",
                "sat_id": "G02",
                "time": pd.Timestamp("2026-05-20T00:00:30Z"),
                "el": 5.0,
                "L1_value": 1.0,
                "L2_value": 2.0,
                "C1_value": 100.0,
                "C2_value": 104.0,
                "S1_value": 45.0,
                "S2_value": 42.0,
                "L1_lli": 0,
                "L2_lli": 0,
            },
            {
                "station_id": "0001",
                "system": "G",
                "sat_id": "G03",
                "time": pd.Timestamp("2026-05-20T00:01:00Z"),
                "el": 30.0,
                "L1_value": 1.0,
                "L2_value": 2.0,
                "C1_value": 100.0,
                "C2_value": 400.0,
                "S1_value": 20.0,
                "S2_value": 42.0,
                "L1_lli": 1,
                "L2_lli": 0,
            },
        ]
    )

    filtered = apply_quality_control(
        frame,
        QualityControlConfig(
            min_elevation_deg=15.0,
            min_s1_dbhz=35.0,
            min_s2_dbhz=35.0,
            max_abs_code_geometry_free_m=50.0,
        ),
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["sat_id"] == "G01"


def test_annotate_quality_flags_marks_failure_reasons() -> None:
    frame = pd.DataFrame(
        [
            {
                "station_id": "0001",
                "system": "G",
                "sat_id": "G01",
                "time": pd.Timestamp("2026-05-20T00:00:00Z"),
                "el": 10.0,
                "L1_value": 1.0,
                "L2_value": 2.0,
                "C1_value": 100.0,
                "C2_value": 110.0,
                "S1_value": 50.0,
                "S2_value": 50.0,
                "L1_lli": 0,
                "L2_lli": 1,
            }
        ]
    )

    annotated = annotate_quality_flags(
        frame,
        QualityControlConfig(min_elevation_deg=15.0, max_abs_code_geometry_free_m=20.0),
    )

    row = annotated.iloc[0]
    assert bool(row["qc_pass_dual_frequency"]) is True
    assert bool(row["qc_pass_elevation"]) is False
    assert bool(row["qc_pass_lli"]) is False
    assert bool(row["qc_pass_code_geometry_free"]) is True
    assert bool(row["qc_pass"]) is False
