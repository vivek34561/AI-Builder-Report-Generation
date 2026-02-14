from __future__ import annotations

import argparse
from pathlib import Path

from src.step2.merge_layer import run_merge_layer


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Merge + de-duplicate + conflict-detect inspection and thermal facts by area "
            "(writes merged_area_data.json)"
        )
    )
    parser.add_argument(
        "--inspection-facts",
        default="outputs/step2/inspection_facts.json",
        help="Path to inspection_facts.json",
    )
    parser.add_argument(
        "--thermal-facts",
        default="outputs/step2/thermal_facts.json",
        help="Path to thermal_facts.json",
    )
    parser.add_argument(
        "--out",
        default="outputs/merged",
        help="Output directory (merged_area_data.json is written here)",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.92,
        help="De-dup similarity threshold (0-1). Higher = stricter.",
    )
    args = parser.parse_args()

    insp = Path(args.inspection_facts)
    therm = Path(args.thermal_facts)
    if not insp.exists() and not therm.exists():
        raise SystemExit(
            "Neither facts file exists. Expected at least one of:\n"
            f"- {insp}\n"
            f"- {therm}\n\n"
            "Tip: run Step 2 with GROQ_API_KEY set to generate facts JSON."
        )

    out_file = run_merge_layer(
        inspection_facts_path=str(insp),
        thermal_facts_path=str(therm),
        out_dir=str(Path(args.out)),
        similarity_threshold=float(args.similarity_threshold),
    )
    print(str(out_file.resolve()))


if __name__ == "__main__":
    main()
