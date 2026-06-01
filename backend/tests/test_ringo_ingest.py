from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas import DatetimeTZDtype

from app.config.gnss import ObservationPriority, default_observation_priorities
from app.processing.ringo_ingest import (
    load_ringo_csv,
    normalize_wide_observations,
    select_priority_observations,
    wide_to_long_observations,
)


def test_load_ringo_csv_and_selection(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "\n".join(
            [
                "> PRN,                    time,      az,     el,            C1C,            L1C,            C2W,            L2W,            S1C,            S2W",
                "  G01, 2026-05-20 00:00:00.000,  225.36,  84.75,   20097557.797,  105613442.765,   20097564.117,   82296254.156,         50.800,         46.400",
                "  G01, 2026-05-20 00:00:30.000,  225.80,  84.99,   20095907.906,  105604771.911,   20095914.031,   82289497.656,         50.200,         46.500",
            ]
        )
    )

    frame = load_ringo_csv(csv_path)
    assert list(frame.columns[:4]) == ["PRN", "time", "az", "el"]
    assert isinstance(frame["time"].dtype, DatetimeTZDtype)
    assert frame["az"].dtype == "float64"

    wide = normalize_wide_observations(frame, station_id="0001", source_path=csv_path)
    selected = select_priority_observations(
        wide,
        ObservationPriority(
            system="G",
            l1_priority=("L1C",),
            l2_priority=("L2W",),
            c1_priority=("C1C",),
            c2_priority=("C2W",),
            s1_priority=("S1C",),
            s2_priority=("S2W",),
        ),
    )
    long_frame = wide_to_long_observations(wide)

    assert {"az", "el", "L1_value", "L2_value", "C1_value", "C2_value"}.issubset(selected.columns)
    assert selected.iloc[0]["L1_code"] == "L1C"
    assert selected.iloc[0]["L2_code"] == "L2W"
    assert selected.iloc[0]["az"] == 225.36
    assert set(long_frame["obs_code"].unique()) >= {"C1C", "L1C", "C2W", "L2W"}


def test_select_priority_observations_multi_constellation() -> None:
    wide = pd.DataFrame(
        [
            {
                "station_id": "0001",
                "system": "G",
                "sat_id": "G01",
                "time": pd.Timestamp("2026-05-20T00:00:00Z"),
                "source_path": "sample.csv",
                "C1C": 1.0,
                "L1C": 2.0,
                "C2W": 3.0,
                "L2W": 4.0,
                "S1C": 5.0,
                "S2W": 6.0,
            },
            {
                "station_id": "0001",
                "system": "E",
                "sat_id": "E11",
                "time": pd.Timestamp("2026-05-20T00:00:00Z"),
                "source_path": "sample.csv",
                "C1X": 11.0,
                "L1X": 12.0,
                "C5X": 13.0,
                "L5X": 14.0,
                "S1X": 15.0,
                "S5X": 16.0,
            },
            {
                "station_id": "0001",
                "system": "R",
                "sat_id": "R05",
                "time": pd.Timestamp("2026-05-20T00:00:00Z"),
                "source_path": "sample.csv",
                "C1P": 21.0,
                "L1P": 22.0,
                "C2P": 23.0,
                "L2P": 24.0,
                "S1P": 25.0,
                "S2P": 26.0,
            },
        ]
    )

    selected = select_priority_observations(wide, default_observation_priorities())

    assert set(selected["system"]) == {"G", "E", "R"}
    by_system = {row["system"]: row for _, row in selected.iterrows()}
    assert by_system["G"]["L1_code"] == "L1C"
    assert by_system["G"]["L2_code"] == "L2W"
    assert by_system["E"]["L1_code"] == "L1X"
    assert by_system["E"]["L2_code"] == "L5X"
    assert by_system["R"]["L1_code"] == "L1P"
    assert by_system["R"]["L2_code"] == "L2P"
