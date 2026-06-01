from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.processing.anomaly import AnomalyProcessingConfig, build_anomaly_grid
from app.processing.grid import GridProcessingConfig, build_tec_grid
from app.config.gnss import ObservationPriority
from app.processing.ipp import IppProcessingConfig, build_ipp_points
from app.processing.ringo_ingest import (
    load_ringo_csv,
    normalize_wide_observations,
    select_priority_observations,
)
from app.processing.station_metadata import parse_qc_summary
from app.processing.stec import StecProcessingConfig, build_stec_arcs


def test_synthetic_pipeline_end_to_end(tmp_path: Path) -> None:
    csv_path = tmp_path / "synthetic.csv"
    qc_path = tmp_path / "synthetic.qc.log"
    csv_lines = [
        "> PRN,                    time,      az,     el,            C1C,            L1C,            C2W,            L2W,            S1C,            S2W",
    ]
    for idx in range(12):
        csv_lines.append(
            f"  G01, 2026-05-20 00:{idx // 2:02d}:{(idx % 2) * 30:02d}.000,  180.00,  80.00,   20000000.000,  100000000.{idx:03d},   20000005.000,   80000000.{idx:03d},         50.000,         45.000"
        )
    csv_path.write_text("\n".join(csv_lines))
    qc_path.write_text(
        "\n".join(
            [
                "# Marker                 : 0001",
                "# Approx XYZ             :  -3522845.1233,   2777143.9836,   4518959.0510",
            ]
        )
    )

    frame = load_ringo_csv(csv_path)
    wide = normalize_wide_observations(frame, station_id="0001", source_path=csv_path)
    selected = select_priority_observations(wide, ObservationPriority())
    stec = build_stec_arcs(selected, StecProcessingConfig(gap_seconds=300, phase_jump_threshold_tecu=9999, min_arc_points=10))
    station = pd.DataFrame([parse_qc_summary(qc_path)])
    ipp = build_ipp_points(stec, station, IppProcessingConfig(shell_height_km=350.0, min_elevation_deg=15.0))
    grid = build_tec_grid(ipp, GridProcessingConfig(time_step="15min", lat_resolution_deg=0.5, lon_resolution_deg=0.5))
    anomaly = build_anomaly_grid(grid, AnomalyProcessingConfig(std_floor_tecu=0.1))

    assert not selected.empty
    assert not stec.empty
    assert not ipp.empty
    assert not grid.empty
    assert not anomaly.empty
    assert {"stec_leveled_tecu", "ipp_lat_deg", "ipp_lon_deg", "vtec_tecu"}.issubset(ipp.columns)
    assert {"median_vtec_tecu", "sample_count"}.issubset(grid.columns)
    assert {"baseline_vtec_tecu", "z_score"}.issubset(anomaly.columns)
