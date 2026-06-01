from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from app.processing.regional_vtec import (
    RegionalVtecConfig,
    build_regional_vtec_grid,
    build_regional_vtec_grid_from_parquet,
    list_time_bins_for_parquet,
)


def test_build_regional_vtec_grid_solves_continuous_field_on_fixed_grid() -> None:
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
                "ipp_lat_deg": 35.4,
                "ipp_lon_deg": 140.4,
                "vtec_tecu": 14.0,
                "stec_leveled_tecu": 15.0,
            },
        ]
    )
    grid = build_regional_vtec_grid(
        ipp,
        RegionalVtecConfig(
            time_step="15min",
            lat_resolution_deg=0.5,
            lon_resolution_deg=0.5,
            lat_min_deg=35.0,
            lat_max_deg=36.0,
            lon_min_deg=140.0,
            lon_max_deg=141.0,
            smoothing_lambda=0.1,
        ),
    )

    assert len(grid) == 4
    southwest = grid.loc[(grid["grid_lat_deg"] == 35.25) & (grid["grid_lon_deg"] == 140.25)].iloc[0]
    northeast = grid.loc[(grid["grid_lat_deg"] == 35.75) & (grid["grid_lon_deg"] == 140.75)].iloc[0]
    assert southwest["sample_count"] >= 1
    assert math.isclose(southwest["median_vtec_tecu"], southwest["mean_vtec_tecu"], rel_tol=1e-12)
    assert southwest["median_vtec_tecu"] < northeast["median_vtec_tecu"]
    assert grid["time_bin"].nunique() == 1


def test_build_regional_vtec_grid_from_parquet_processes_time_bins_incrementally(tmp_path: Path) -> None:
    ipp = pd.DataFrame(
        [
            {
                "time": pd.Timestamp("2026-05-20T00:01:00Z"),
                "ipp_lat_deg": 35.1,
                "ipp_lon_deg": 140.1,
                "vtec_tecu": 10.0,
                "stec_leveled_tecu": 11.0,
                "mapping_function": 1.2,
            },
            {
                "time": pd.Timestamp("2026-05-20T00:16:00Z"),
                "ipp_lat_deg": 35.4,
                "ipp_lon_deg": 140.4,
                "vtec_tecu": 14.0,
                "stec_leveled_tecu": 15.0,
                "mapping_function": 1.3,
            },
        ]
    )
    path = tmp_path / "ipp.parquet"
    ipp.to_parquet(path, index=False)
    config = RegionalVtecConfig(
        time_step="15min",
        lat_resolution_deg=0.5,
        lon_resolution_deg=0.5,
        lat_min_deg=35.0,
        lat_max_deg=36.0,
        lon_min_deg=140.0,
        lon_max_deg=141.0,
        smoothing_lambda=0.1,
    )

    bins = list_time_bins_for_parquet(path, config)
    grid = build_regional_vtec_grid_from_parquet(path, config)

    assert len(bins) == 2
    assert grid["time_bin"].nunique() == 2
