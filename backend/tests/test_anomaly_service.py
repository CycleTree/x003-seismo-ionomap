from __future__ import annotations

import math

import pandas as pd

from app.services.anomaly_grid import anomaly_grid_to_geojson, stats_for_mode, value_column_for_mode


def test_value_column_for_mode_maps_supported_modes() -> None:
    assert value_column_for_mode("anomaly") == "z_score"
    assert value_column_for_mode("detrended") == "delta_vtec_tecu"
    assert value_column_for_mode("vtec") == "median_vtec_tecu"


def test_anomaly_grid_to_geojson_uses_selected_display_mode() -> None:
    frame = pd.DataFrame(
        [
            {
                "time_bin": pd.Timestamp("2026-05-20T00:00:00Z"),
                "grid_lat_deg": 35.25,
                "grid_lon_deg": 140.25,
                "sample_count": 3,
                "median_vtec_tecu": 12.0,
                "baseline_vtec_tecu": 10.0,
                "baseline_mode": "quiet_day",
                "delta_vtec_tecu": 2.0,
                "z_score": 1.5,
                "abs_z_score": 1.5,
                "local_time_slot": "09:00",
            }
        ]
    )

    geojson = anomaly_grid_to_geojson(frame, mode="detrended")
    feature = geojson["features"][0]

    assert feature["properties"]["display_mode"] == "detrended"
    assert math.isclose(feature["properties"]["display_value"], 2.0, rel_tol=1e-12)
    assert feature["properties"]["baseline_mode"] == "quiet_day"


def test_stats_for_mode_uses_requested_metric() -> None:
    frame = pd.DataFrame(
        [
            {"z_score": -2.0, "delta_vtec_tecu": -4.0, "median_vtec_tecu": 10.0},
            {"z_score": 1.0, "delta_vtec_tecu": 2.0, "median_vtec_tecu": 14.0},
        ]
    )

    stats = stats_for_mode(frame, "vtec")

    assert stats["cellCount"] == 2
    assert math.isclose(float(stats["maxAbsValue"]), 14.0, rel_tol=1e-12)
    assert math.isclose(float(stats["meanValue"]), 12.0, rel_tol=1e-12)
