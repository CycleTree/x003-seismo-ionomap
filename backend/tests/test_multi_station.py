from __future__ import annotations

from pathlib import Path

from app.processing.multi_station import collect_station_pairs


def test_collect_station_pairs_matches_obs_and_nav(tmp_path: Path) -> None:
    (tmp_path / "00011400.26d.gz").write_text("")
    (tmp_path / "00011400.26N.tar.gz").write_text("")
    (tmp_path / "00021400.26d.gz").write_text("")
    (tmp_path / "99991400.26N.tar.gz").write_text("")

    pairs = collect_station_pairs(tmp_path)
    assert len(pairs) == 1
    assert pairs[0].station_code == "0001"
    assert pairs[0].stem == "00011400"
