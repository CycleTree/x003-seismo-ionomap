from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.config.gnss import ObservationPriority


BASE_COLUMNS = ("PRN", "time")


@dataclass(frozen=True)
class IngestArtifacts:
    wide_path: Path
    long_path: Path
    selected_path: Path


def load_ringo_csv(csv_path: str | Path) -> pd.DataFrame:
    csv_path = Path(csv_path)
    frame = pd.read_csv(csv_path, sep=r",\s*", engine="python")
    frame.columns = [column.replace(">", "").strip() for column in frame.columns]
    if not {"PRN", "time"}.issubset(frame.columns):
        raise ValueError(f"Unexpected rnxcsv columns in {csv_path}")
    for column in frame.select_dtypes(include="object").columns:
        frame[column] = frame[column].astype(str).str.strip()
    frame = frame.loc[
        (frame["PRN"] != "PRN")
        & (frame["time"] != "time")
        & (frame["PRN"] != "")
        & (frame["time"] != "")
    ].copy()
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    for column in frame.columns:
        if column in BASE_COLUMNS:
            continue
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def normalize_wide_observations(
    frame: pd.DataFrame,
    *,
    station_id: str,
    source_path: str | Path | None = None,
) -> pd.DataFrame:
    wide = frame.copy()
    wide = wide.rename(columns={"PRN": "sat_id"})
    wide.insert(0, "station_id", station_id)
    wide.insert(1, "system", wide["sat_id"].str[0])
    if source_path is not None:
        wide["source_path"] = str(source_path)
    return wide


def wide_to_long_observations(wide: pd.DataFrame) -> pd.DataFrame:
    obs_columns = [
        column
        for column in wide.columns
        if column not in {"station_id", "system", "sat_id", "time", "source_path"}
    ]
    long_frame = wide.melt(
        id_vars=[column for column in ["station_id", "system", "sat_id", "time", "source_path"] if column in wide.columns],
        value_vars=obs_columns,
        var_name="obs_code",
        value_name="value",
    )
    long_frame = long_frame.dropna(subset=["value"]).reset_index(drop=True)
    return long_frame


def select_priority_observations(
    wide: pd.DataFrame,
    priority: ObservationPriority,
) -> pd.DataFrame:
    frame = wide.loc[wide["system"] == priority.system].copy()
    selected = frame[["station_id", "system", "sat_id", "time"]].copy()
    if "source_path" in frame.columns:
        selected["source_path"] = frame["source_path"]

    for alias, codes in {
        "L1": priority.l1_priority,
        "L2": priority.l2_priority,
        "C1": priority.c1_priority,
        "C2": priority.c2_priority,
        "S1": priority.s1_priority,
        "S2": priority.s2_priority,
    }.items():
        value_column = f"{alias}_value"
        code_column = f"{alias}_code"
        selected[value_column] = pd.NA
        selected[code_column] = pd.NA
        for code in codes:
            if code not in frame.columns:
                continue
            mask = selected[value_column].isna() & frame[code].notna()
            selected.loc[mask, value_column] = frame.loc[mask, code]
            selected.loc[mask, code_column] = code

    return selected


def export_observation_products(
    *,
    wide: pd.DataFrame,
    long_frame: pd.DataFrame,
    selected: pd.DataFrame,
    output_dir: str | Path,
    prefix: str,
) -> IngestArtifacts:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    wide_path = output_dir / f"{prefix}.wide.parquet"
    long_path = output_dir / f"{prefix}.long.parquet"
    selected_path = output_dir / f"{prefix}.selected.parquet"
    wide.to_parquet(wide_path, index=False)
    long_frame.to_parquet(long_path, index=False)
    selected.to_parquet(selected_path, index=False)
    return IngestArtifacts(
        wide_path=wide_path,
        long_path=long_path,
        selected_path=selected_path,
    )
