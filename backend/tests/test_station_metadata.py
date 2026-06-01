from __future__ import annotations

from pathlib import Path

from app.processing.station_metadata import parse_qc_summary


def test_parse_qc_summary_extracts_station_metadata(tmp_path: Path) -> None:
    qc_path = tmp_path / "sample.qc.log"
    qc_path.write_text(
        "\n".join(
            [
                "# Marker                 : 0001",
                "# Receiver               : TRIMBLE ALLOY",
                "# Antenna                : TRM59800.80     GSI3",
                "# Approx XYZ             :  -3522845.1233,   2777143.9836,   4518959.0510",
            ]
        )
    )

    metadata = parse_qc_summary(qc_path)
    assert metadata["station_id"] == "0001"
    assert metadata["receiver"] == "TRIMBLE ALLOY"
    assert metadata["antenna"].startswith("TRM59800.80")
    assert abs(float(metadata["lat_deg"]) - 45.4) < 0.5
    assert abs(float(metadata["lon_deg"]) - 141.75) < 0.5

