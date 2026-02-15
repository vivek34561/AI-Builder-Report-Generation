from __future__ import annotations

from pathlib import Path

from .models import DDRReport


class MarkdownFormatter:
    """Format DDR report as Markdown."""

    @staticmethod
    def format(report: DDRReport) -> str:
        """Generate markdown formatted DDR report."""
        lines = []

        # Header
        lines.append(f"# {report.property_name}")
        lines.append(f"\n**Report Date:** {report.report_date}\n")
        lines.append("---\n")

        # 1. Property Issue Summary
        lines.append("## 1. Property Issue Summary\n")
        summary = report.property_issue_summary
        lines.append(f"- **Total Areas Inspected:** {summary.total_areas_inspected}")
        lines.append(f"- **Areas with Issues:** {summary.areas_with_issues}")
        lines.append(f"- **Overall Risk Level:** {summary.overall_risk_level}\n")

        lines.append("**Severity Breakdown:**")
        lines.append(f"- Critical: {summary.critical_count}")
        lines.append(f"- High: {summary.high_count}")
        lines.append(f"- Medium: {summary.medium_count}")
        lines.append(f"- Low: {summary.low_count}\n")

        if summary.key_findings:
            lines.append("**Key Findings:**")
            for finding in summary.key_findings:
                lines.append(f"- {finding}")
        lines.append("\n---\n")

        # 2. Area-wise Observations
        lines.append("## 2. Area-wise Observations\n")
        for obs in report.area_observations:
            lines.append(f"### {obs.area_name}\n")
            lines.append(f"**Inspection Findings:** {obs.inspection_summary}\n")
            lines.append(f"**Thermal Findings:** {obs.thermal_summary}\n")

            if obs.has_conflict:
                lines.append(f"**⚠️ CONFLICT DETECTED:** {obs.conflict_description}\n")

            lines.append("")

        lines.append("---\n")

        # 3. Probable Root Cause
        lines.append("## 3. Probable Root Cause\n")
        if report.root_causes:
            for rc in report.root_causes:
                lines.append(f"### {rc.area_name}\n")
                lines.append(f"**Probable Cause:** {rc.probable_cause}\n")
                lines.append(f"**Reasoning:** {rc.reasoning}\n")
                lines.append(f"**Confidence Level:** {rc.confidence}\n")

                if rc.supporting_evidence:
                    lines.append("**Supporting Evidence:**")
                    for evidence in rc.supporting_evidence:
                        lines.append(f"- {evidence}")
                    lines.append("")

                if rc.evidence_gaps:
                    lines.append("**Evidence Gaps:**")
                    for gap in rc.evidence_gaps:
                        lines.append(f"- {gap}")
                    lines.append("")

                lines.append("")
        else:
            lines.append("Not Available\n")

        lines.append("---\n")

        # 4. Severity Assessment
        lines.append("## 4. Severity Assessment (with Reasoning)\n")
        if report.severity_assessments:
            for sev in report.severity_assessments:
                lines.append(f"### {sev.area_name}\n")
                lines.append(f"**Severity Level:** {sev.severity_level}\n")
                lines.append(f"**Reasoning:** {sev.reasoning}\n")

                if sev.risk_factors:
                    lines.append("**Risk Factors:**")
                    for factor in sev.risk_factors:
                        lines.append(f"- {factor}")
                    lines.append("")

                lines.append("")
        else:
            lines.append("Not Available\n")

        lines.append("---\n")

        # 5. Recommended Actions
        lines.append("## 5. Recommended Actions\n")
        if report.recommended_actions:
            # Group by priority
            immediate = [a for a in report.recommended_actions if a.priority == "Immediate"]
            short_term = [a for a in report.recommended_actions if a.priority == "Short-term"]
            medium_term = [a for a in report.recommended_actions if a.priority == "Medium-term"]
            monitoring = [a for a in report.recommended_actions if a.priority == "Monitoring"]

            if immediate:
                lines.append("### Immediate Actions (Critical Priority)\n")
                for action in immediate:
                    lines.append(f"**{action.area}**")
                    lines.append(f"- Action: {action.action}")
                    lines.append(f"- Rationale: {action.rationale}\n")

            if short_term:
                lines.append("### Short-term Actions (High Priority)\n")
                for action in short_term:
                    lines.append(f"**{action.area}**")
                    lines.append(f"- Action: {action.action}")
                    lines.append(f"- Rationale: {action.rationale}\n")

            if medium_term:
                lines.append("### Medium-term Actions\n")
                for action in medium_term:
                    lines.append(f"**{action.area}**")
                    lines.append(f"- Action: {action.action}")
                    lines.append(f"- Rationale: {action.rationale}\n")

            if monitoring:
                lines.append("### Monitoring Recommendations\n")
                for action in monitoring:
                    lines.append(f"**{action.area}**")
                    lines.append(f"- Action: {action.action}")
                    lines.append(f"- Rationale: {action.rationale}\n")
        else:
            lines.append("Not Available\n")

        lines.append("---\n")

        # 6. Additional Notes
        lines.append("## 6. Additional Notes\n")
        if report.additional_notes:
            for note in report.additional_notes:
                lines.append(f"{note}\n")
        else:
            lines.append("Not Available\n")

        lines.append("---\n")

        # 7. Missing or Unclear Information
        lines.append("## 7. Missing or Unclear Information\n")
        if report.missing_information:
            for missing in report.missing_information:
                lines.append(f"### {missing.category}\n")
                lines.append(f"**Description:** {missing.description}\n")
                lines.append(f"**Impact:** {missing.impact}\n")
                if missing.affected_areas:
                    lines.append(f"**Affected Areas:** {', '.join(missing.affected_areas)}\n")
                lines.append("")
        else:
            lines.append("Not Available\n")

        return "\n".join(lines)


class PlainTextFormatter:
    """Format DDR report as plain text."""

    @staticmethod
    def format(report: DDRReport) -> str:
        """Generate plain text formatted DDR report."""
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append(report.property_name.center(80))
        lines.append(f"Report Date: {report.report_date}".center(80))
        lines.append("=" * 80)
        lines.append("")

        # 1. Property Issue Summary
        lines.append("1. PROPERTY ISSUE SUMMARY")
        lines.append("-" * 80)
        summary = report.property_issue_summary
        lines.append(f"Total Areas Inspected: {summary.total_areas_inspected}")
        lines.append(f"Areas with Issues: {summary.areas_with_issues}")
        lines.append(f"Overall Risk Level: {summary.overall_risk_level}")
        lines.append("")
        lines.append("Severity Breakdown:")
        lines.append(f"  Critical: {summary.critical_count}")
        lines.append(f"  High: {summary.high_count}")
        lines.append(f"  Medium: {summary.medium_count}")
        lines.append(f"  Low: {summary.low_count}")
        lines.append("")

        if summary.key_findings:
            lines.append("Key Findings:")
            for finding in summary.key_findings:
                lines.append(f"  - {finding}")
        lines.append("")

        # 2. Area-wise Observations
        lines.append("2. AREA-WISE OBSERVATIONS")
        lines.append("-" * 80)
        for obs in report.area_observations:
            lines.append(f"\n{obs.area_name}")
            lines.append(f"  Inspection Findings: {obs.inspection_summary}")
            lines.append(f"  Thermal Findings: {obs.thermal_summary}")
            if obs.has_conflict:
                lines.append(f"  *** CONFLICT DETECTED: {obs.conflict_description}")
            lines.append("")

        # 3. Probable Root Cause
        lines.append("3. PROBABLE ROOT CAUSE")
        lines.append("-" * 80)
        if report.root_causes:
            for rc in report.root_causes:
                lines.append(f"\n{rc.area_name}")
                lines.append(f"  Probable Cause: {rc.probable_cause}")
                lines.append(f"  Reasoning: {rc.reasoning}")
                lines.append(f"  Confidence Level: {rc.confidence}")

                if rc.supporting_evidence:
                    lines.append("  Supporting Evidence:")
                    for evidence in rc.supporting_evidence:
                        lines.append(f"    - {evidence}")

                if rc.evidence_gaps:
                    lines.append("  Evidence Gaps:")
                    for gap in rc.evidence_gaps:
                        lines.append(f"    - {gap}")
                lines.append("")
        else:
            lines.append("Not Available")
        lines.append("")

        # 4. Severity Assessment
        lines.append("4. SEVERITY ASSESSMENT (WITH REASONING)")
        lines.append("-" * 80)
        if report.severity_assessments:
            for sev in report.severity_assessments:
                lines.append(f"\n{sev.area_name}")
                lines.append(f"  Severity Level: {sev.severity_level}")
                lines.append(f"  Reasoning: {sev.reasoning}")

                if sev.risk_factors:
                    lines.append("  Risk Factors:")
                    for factor in sev.risk_factors:
                        lines.append(f"    - {factor}")
                lines.append("")
        else:
            lines.append("Not Available")
        lines.append("")

        # 5. Recommended Actions
        lines.append("5. RECOMMENDED ACTIONS")
        lines.append("-" * 80)
        if report.recommended_actions:
            for priority in ["Immediate", "Short-term", "Medium-term", "Monitoring"]:
                actions = [a for a in report.recommended_actions if a.priority == priority]
                if actions:
                    lines.append(f"\n{priority} Actions:")
                    for action in actions:
                        lines.append(f"  {action.area}")
                        lines.append(f"    Action: {action.action}")
                        lines.append(f"    Rationale: {action.rationale}")
                        lines.append("")
        else:
            lines.append("Not Available")
        lines.append("")

        # 6. Additional Notes
        lines.append("6. ADDITIONAL NOTES")
        lines.append("-" * 80)
        if report.additional_notes:
            for note in report.additional_notes:
                lines.append(note)
                lines.append("")
        else:
            lines.append("Not Available")
        lines.append("")

        # 7. Missing Information
        lines.append("7. MISSING OR UNCLEAR INFORMATION")
        lines.append("-" * 80)
        if report.missing_information:
            for missing in report.missing_information:
                lines.append(f"\n{missing.category}")
                lines.append(f"  Description: {missing.description}")
                lines.append(f"  Impact: {missing.impact}")
                if missing.affected_areas:
                    lines.append(f"  Affected Areas: {', '.join(missing.affected_areas)}")
                lines.append("")
        else:
            lines.append("Not Available")

        lines.append("")
        lines.append("=" * 80)
        lines.append("END OF REPORT".center(80))
        lines.append("=" * 80)

        return "\n".join(lines)


class PDFFormatter:
    """Format DDR report as PDF (via markdown conversion)."""

    @staticmethod
    def format(report: DDRReport, output_path: Path) -> None:
        """
        Generate PDF formatted DDR report.
        Uses markdown as intermediate format and converts to PDF.
        """
        try:
            import markdown
            from weasyprint import HTML
        except ImportError:
            raise ImportError(
                "PDF generation requires 'markdown' and 'weasyprint' packages. "
                "Install with: pip install markdown weasyprint"
            )

        # Generate markdown
        md_content = MarkdownFormatter.format(report)

        # Convert markdown to HTML
        html_content = markdown.markdown(
            md_content, extensions=["tables", "fenced_code", "nl2br"]
        )

        # Add CSS styling for professional appearance
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 20px;
                    color: #333;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    border-bottom: 2px solid #95a5a6;
                    padding-bottom: 8px;
                    margin-top: 30px;
                }}
                h3 {{
                    color: #7f8c8d;
                    margin-top: 20px;
                }}
                hr {{
                    border: none;
                    border-top: 1px solid #bdc3c7;
                    margin: 20px 0;
                }}
                ul {{
                    margin-left: 20px;
                }}
                strong {{
                    color: #2c3e50;
                }}
                .conflict {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 10px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        # Convert HTML to PDF
        HTML(string=styled_html).write_pdf(output_path)


def save_report(report: DDRReport, output_dir: Path, formats: list[str]) -> dict[str, Path]:
    """
    Save DDR report in specified formats.

    Args:
        report: DDR report to save
        output_dir: Output directory
        formats: List of formats ('markdown', 'pdf', 'txt')

    Returns:
        Dictionary mapping format to output file path
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_files = {}

    if "markdown" in formats or "md" in formats:
        md_path = output_dir / "DDR_Report.md"
        md_content = MarkdownFormatter.format(report)
        md_path.write_text(md_content, encoding="utf-8")
        saved_files["markdown"] = md_path

    if "txt" in formats or "text" in formats:
        txt_path = output_dir / "DDR_Report.txt"
        txt_content = PlainTextFormatter.format(report)
        txt_path.write_text(txt_content, encoding="utf-8")
        saved_files["text"] = txt_path

    if "pdf" in formats:
        pdf_path = output_dir / "DDR_Report.pdf"
        try:
            PDFFormatter.format(report, pdf_path)
            saved_files["pdf"] = pdf_path
        except ImportError as e:
            print(f"Warning: Could not generate PDF - {e}")
            print("Skipping PDF generation. Install with: pip install markdown weasyprint")

    return saved_files
