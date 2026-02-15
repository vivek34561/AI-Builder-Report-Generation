from __future__ import annotations

import argparse
from pathlib import Path

from src.step3.reasoning_engine import run_analytical_reasoning


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Step 3: Analytical Reasoning Layer - Infer root causes, assign severity, "
            "and identify missing information using controlled LLM reasoning"
        )
    )
    parser.add_argument(
        "--merged-data",
        default="outputs/merged/merged_area_data.json",
        help="Path to merged_area_data.json from Step 2",
    )
    parser.add_argument(
        "--out",
        default="outputs/step3",
        help="Output directory (analytical_reasoning.json is written here)",
    )
    args = parser.parse_args()

    merged_path = Path(args.merged_data)
    if not merged_path.exists():
        raise SystemExit(
            f"Merged data file not found: {merged_path}\n\n"
            "Tip: Run the merge layer first:\n"
            "  python run_merge_area_data.py --inspection-facts outputs/step2/inspection_facts.json "
            "--thermal-facts outputs/step2/thermal_facts.json --out outputs/merged"
        )

    out_file = run_analytical_reasoning(
        merged_data_path=str(merged_path),
        out_dir=str(Path(args.out)),
    )
    print(f"\n✓ Analytical reasoning complete: {out_file.resolve()}")


if __name__ == "__main__":
    main()
