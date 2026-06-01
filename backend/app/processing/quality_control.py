from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class QualityControlConfig:
    min_elevation_deg: float | None = None
    min_s1_dbhz: float | None = None
    min_s2_dbhz: float | None = None
    reject_on_lli: bool = True
    max_abs_code_geometry_free_m: float | None = None
    require_dual_frequency: bool = True


def annotate_quality_flags(
    frame: pd.DataFrame,
    config: QualityControlConfig,
) -> pd.DataFrame:
    annotated = frame.copy()

    if config.require_dual_frequency:
        annotated["qc_pass_dual_frequency"] = (
            annotated["L1_value"].notna()
            & annotated["L2_value"].notna()
            & annotated["C1_value"].notna()
            & annotated["C2_value"].notna()
        )
    else:
        annotated["qc_pass_dual_frequency"] = True

    if config.min_elevation_deg is not None and "el" in annotated.columns:
        annotated["qc_pass_elevation"] = annotated["el"].ge(config.min_elevation_deg).fillna(False)
    else:
        annotated["qc_pass_elevation"] = True

    if config.min_s1_dbhz is not None and "S1_value" in annotated.columns:
        annotated["qc_pass_s1"] = annotated["S1_value"].ge(config.min_s1_dbhz).fillna(False)
    else:
        annotated["qc_pass_s1"] = True

    if config.min_s2_dbhz is not None and "S2_value" in annotated.columns:
        annotated["qc_pass_s2"] = annotated["S2_value"].ge(config.min_s2_dbhz).fillna(False)
    else:
        annotated["qc_pass_s2"] = True

    if config.reject_on_lli and any(column in annotated.columns for column in ("L1_lli", "L2_lli")):
        l1_ok = annotated["L1_lli"].fillna(0).eq(0) if "L1_lli" in annotated.columns else True
        l2_ok = annotated["L2_lli"].fillna(0).eq(0) if "L2_lli" in annotated.columns else True
        annotated["qc_pass_lli"] = l1_ok & l2_ok
    else:
        annotated["qc_pass_lli"] = True

    if config.max_abs_code_geometry_free_m is not None:
        code_geometry_free = annotated["C2_value"] - annotated["C1_value"]
        annotated["qc_pass_code_geometry_free"] = (
            code_geometry_free.abs().le(config.max_abs_code_geometry_free_m).fillna(False)
        )
    else:
        annotated["qc_pass_code_geometry_free"] = True

    quality_columns = [column for column in annotated.columns if column.startswith("qc_pass_")]
    annotated["qc_pass"] = annotated[quality_columns].all(axis=1)
    return annotated


def apply_quality_control(
    frame: pd.DataFrame,
    config: QualityControlConfig,
) -> pd.DataFrame:
    annotated = annotate_quality_flags(frame, config)
    return annotated.loc[annotated["qc_pass"]].copy().reset_index(drop=True)
