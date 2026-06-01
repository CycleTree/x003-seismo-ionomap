from __future__ import annotations

import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.processing.bias import extract_bias_tables
from app.processing.stec import load_stec_arcs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract receiver, satellite, and arc bias tables from STEC arcs.")
    parser.add_argument("input_parquet", help="Path to stec_arcs parquet")
    parser.add_argument(
        "--output-dir",
        default="data/intermediate/bias_tables",
        help="Directory for generated bias tables",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_path = Path(args.input_parquet)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stec_arcs = load_stec_arcs(input_path)
    bias_tables = extract_bias_tables(stec_arcs)
    prefix = input_path.stem.replace(".stec_arcs", "")

    receiver_path = output_dir / f"{prefix}.receiver_biases.parquet"
    satellite_path = output_dir / f"{prefix}.satellite_biases.parquet"
    arc_path = output_dir / f"{prefix}.arc_biases.parquet"

    bias_tables.receiver_biases.to_parquet(receiver_path, index=False)
    bias_tables.satellite_biases.to_parquet(satellite_path, index=False)
    bias_tables.arc_biases.to_parquet(arc_path, index=False)

    print(f"receiver_biases={receiver_path}")
    print(f"satellite_biases={satellite_path}")
    print(f"arc_biases={arc_path}")


if __name__ == "__main__":
    main()
