from __future__ import annotations

import math

import pandas as pd

from app.processing.ipp import IppProcessingConfig, build_ipp_points


def test_build_ipp_points_at_zenith_keeps_station_location_and_vtec() -> None:
    stec_arcs = pd.DataFrame(
        [
            {
                "station_id": "0001",
                "sat_id": "G01",
                "time": pd.Timestamp("2026-05-20T00:00:00Z"),
                "az": 123.0,
                "el": 90.0,
                "stec_leveled_tecu": 42.0,
            }
        ]
    )
    station = pd.DataFrame(
        [
            {
                "station_id": "0001",
                "lat_deg": 35.0,
                "lon_deg": 140.0,
                "height_m": 100.0,
                "x_m": 0.0,
                "y_m": 0.0,
                "z_m": 0.0,
            }
        ]
    )
    ipp = build_ipp_points(stec_arcs, station, IppProcessingConfig(shell_height_km=350.0, min_elevation_deg=15.0))
    row = ipp.iloc[0]
    assert math.isclose(row["mapping_function"], 1.0, rel_tol=1e-12)
    assert math.isclose(row["vtec_tecu"], 42.0, rel_tol=1e-12)
    assert math.isclose(row["ipp_lat_deg"], 35.0, rel_tol=1e-12)
    assert math.isclose(row["ipp_lon_deg"], 140.0, rel_tol=1e-12)

