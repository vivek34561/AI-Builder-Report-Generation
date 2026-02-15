from __future__ import annotations

import argparse
from pathlib import Path

from src.step4.formatters import save_report
from src.step4.report_generator import generate_ddr_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Step 4: Generate DDR (Detailed Diagnostic Report) from analytical reasoning"
    )
    parser.add_argument(
        "--analysis",
        default="outputs/step3/analytical_reasoning.json",
        help="Path to analytical_reasoning.json from Step 3",
    )
    parser.add_argument(
        "--out", default="outputs/ddr", help="Output directory for DDR reports"
    )
    parser.add_argument(
        "--format",
        nargs="+",
        default=["markdown", "txt"],
        choices=["markdown", "md", "pdf", "txt", "text", "all"],
        help="Output format(s): markdown, pdf, txt, or all",
    )
    parser.add_argument(
        "--property-name",
        default="Property Inspection Report",
        help="Property name/identifier for report header",
    )
    args = parser.parse_args()

    # Validate input
    analysis_path = Path(args.analysis)
    if not analysis_path.exists():
        raise SystemExit(
            f"Analysis file not found: {analysis_path}\n\n"
            "Tip: Run Step 3 first:\n"
            "  python run_step3_reasoning.py --merged-data outputs/merged/merged_area_data.json "
            "--out outputs/step3"
        )

    # Handle 'all' format
    formats = args.format
    if "all" in formats:
        formats = ["markdown", "pdf", "txt"]

    print(f"Generating DDR report from: {analysis_path}")
    print(f"Output formats: {', '.join(formats)}")

    # Generate DDR report
    ddr_report = generate_ddr_report(
        analysis_path=str(analysis_path), property_name=args.property_name
    )

    # Save in requested formats
    output_dir = Path(args.out)
    saved_files = save_report(ddr_report, output_dir, formats)

    print(f"\n✓ DDR Report generated successfully!")
    print(f"\nOutput files:")
    for format_name, file_path in saved_files.items():
        print(f"  [{format_name.upper()}] {file_path.resolve()}")

    # Print summary
    summary = ddr_report.property_issue_summary
    print(f"\nReport Summary:")
    print(f"  Total Areas: {summary.total_areas_inspected}")
    print(f"  Areas with Issues: {summary.areas_with_issues}")
    print(f"  Overall Risk: {summary.overall_risk_level}")
    print(f"  Critical: {summary.critical_count} | High: {summary.high_count} | "
          f"Medium: {summary.medium_count} | Low: {summary.low_count}")


if __name__ == "__main__":
    main()
