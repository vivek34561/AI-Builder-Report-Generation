from __future__ import annotations

import argparse
from pathlib import Path

from src.input_layer.config import InputLayerConfig
from src.input_layer.langgraph_input_layer import run_input_layer


def main() -> None:
    parser = argparse.ArgumentParser(description="LangGraph Input Layer: PDF -> per-page JSON via text + OCR")
    parser.add_argument("--inspection", required=True, help="Path to Inspection Report PDF")
    parser.add_argument("--thermal", required=True, help="Path to Thermal Report PDF")
    parser.add_argument("--out", default="outputs", help="Output directory")

    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--ocr-threshold", type=float, default=0.55)
    parser.add_argument("--max-pages", type=int, default=0, help="0 means no limit")

    args = parser.parse_args()

    cfg = InputLayerConfig(
        dpi=args.dpi,
        ocr_confidence_threshold=args.ocr_threshold,
        max_pages=(None if args.max_pages == 0 else args.max_pages),
    )

    out_path = run_input_layer(
        inspection_pdf=str(Path(args.inspection)),
        thermal_pdf=str(Path(args.thermal)),
        out_dir=str(Path(args.out)),
        config=cfg,
    )

    print(out_path)


if __name__ == "__main__":
    main()
