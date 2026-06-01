from __future__ import annotations

import math

import pandas as pd

from app.processing.grid import GridProcessingConfig, build_tec_grid


def test_build_tec_grid_aggregates_points_into_cells() -> None:
    ipp = pd.DataFrame(
        [
            {
                "time": pd.Timestamp("2026-05-20T00:01:00Z"),
                "ipp_lat_deg": 35.1,
                "ipp_lon_deg": 140.1,
                "vtec_tecu": 10.0,
                "stec_leveled_tecu": 11.0,
            },
            {
                "time": pd.Timestamp("2026-05-20T00:10:00Z"),
                "ipp_lat_deg": 35.2,
                "ipp_lon_deg": 140.2,
                "vtec_tecu": 14.0,
                "stec_leveled_tecu": 15.0,
            },
        ]
    )
    grid = build_tec_grid(ipp, GridProcessingConfig(time_step="15min", lat_resolution_deg=0.5, lon_resolution_deg=0.5))
    assert len(grid) == 1
    row = grid.iloc[0]
    assert row["sample_count"] == 2
    assert math.isclose(row["mean_vtec_tecu"], 12.0, rel_tol=1e-12)
    assert math.isclose(row["median_vtec_tecu"], 12.0, rel_tol=1e-12)
    assert math.isclose(row["grid_lat_deg"], 35.25, rel_tol=1e-12)
    assert math.isclose(row["grid_lon_deg"], 140.25, rel_tol=1e-12)

