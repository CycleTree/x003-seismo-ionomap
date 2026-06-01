from __future__ import annotations

import math

import pandas as pd

from app.processing.anomaly import AnomalyProcessingConfig, build_anomaly_grid


def test_build_anomaly_grid_computes_baseline_and_zscore() -> None:
    grid = pd.DataFrame(
        [
            {"time_bin": pd.Timestamp("2026-05-20T00:00:00Z"), "grid_lat_deg": 35.25, "grid_lon_deg": 140.25, "median_vtec_tecu": 10.0},
            {"time_bin": pd.Timestamp("2026-05-20T00:15:00Z"), "grid_lat_deg": 35.25, "grid_lon_deg": 140.25, "median_vtec_tecu": 14.0},
        ]
    )
    anomaly = build_anomaly_grid(grid, AnomalyProcessingConfig(std_floor_tecu=0.1))
    assert len(anomaly) == 2
    assert math.isclose(anomaly.iloc[0]["baseline_vtec_tecu"], 12.0, rel_tol=1e-12)
    assert math.isclose(anomaly.iloc[1]["delta_vtec_tecu"], 2.0, rel_tol=1e-12)
    assert anomaly.iloc[1]["z_score"] > 0

