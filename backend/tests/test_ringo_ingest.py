from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas import DatetimeTZDtype

from app.config.gnss import ObservationPriority
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
    selected = select_priority_observations(wide, ObservationPriority())
    long_frame = wide_to_long_observations(wide)

    assert {"az", "el", "L1_value", "L2_value", "C1_value", "C2_value"}.issubset(selected.columns)
    assert selected.iloc[0]["L1_code"] == "L1C"
    assert selected.iloc[0]["L2_code"] == "L2W"
    assert selected.iloc[0]["az"] == 225.36
    assert set(long_frame["obs_code"].unique()) >= {"C1C", "L1C", "C2W", "L2W"}
