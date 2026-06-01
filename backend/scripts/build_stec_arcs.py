from __future__ import annotations

import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.processing.stec import (
    StecProcessingConfig,
    build_stec_arcs,
    export_stec_arcs,
    load_selected_observations,
)
from app.processing.quality_control import QualityControlConfig, apply_quality_control


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build leveled STEC arc parquet from selected observations.")
    parser.add_argument("input_parquet", help="Path to selected observation parquet")
    parser.add_argument(
        "--output-dir",
        default="data/intermediate/stec_arcs",
        help="Directory for generated STEC arc parquet",
    )
    parser.add_argument("--gap-seconds", type=float, default=300.0)
    parser.add_argument("--phase-jump-threshold-tecu", type=float, default=2.0)
    parser.add_argument("--min-arc-points", type=int, default=10)
    parser.add_argument("--min-elevation-deg", type=float, default=None)
    parser.add_argument("--min-s1-dbhz", type=float, default=None)
    parser.add_argument("--min-s2-dbhz", type=float, default=None)
    parser.add_argument("--max-abs-code-geometry-free-m", type=float, default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = StecProcessingConfig(
        gap_seconds=args.gap_seconds,
        phase_jump_threshold_tecu=args.phase_jump_threshold_tecu,
        min_arc_points=args.min_arc_points,
    )
    input_path = Path(args.input_parquet)
    selected = load_selected_observations(input_path)
    selected = apply_quality_control(
        selected,
        QualityControlConfig(
            min_elevation_deg=args.min_elevation_deg,
            min_s1_dbhz=args.min_s1_dbhz,
            min_s2_dbhz=args.min_s2_dbhz,
            max_abs_code_geometry_free_m=args.max_abs_code_geometry_free_m,
        ),
    )
    stec_arcs = build_stec_arcs(selected, config)
    artifacts = export_stec_arcs(
        stec_arcs,
        output_dir=args.output_dir,
        prefix=input_path.stem.replace(".selected", ""),
    )

    print(f"rows={len(stec_arcs)}")
    print(f"arcs={stec_arcs['arc_id'].nunique()}")
    print(f"output={artifacts.output_path}")


if __name__ == "__main__":
    main()
