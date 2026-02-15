from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..step3.models import AnalyticalReasoningDoc, AreaAnalysis
from .models import (
    AreaObservation,
    DDRReport,
    MissingInfoSection,
    PropertyIssueSummary,
    RecommendedAction,
    RootCauseSection,
    SeveritySection,
)


def generate_property_summary(analysis_doc: AnalyticalReasoningDoc) -> PropertyIssueSummary:
    """
    Generate high-level property issue summary from analytical reasoning.
    """
    total_areas = len(analysis_doc.areas)
    areas_with_issues = 0

    # Count severity levels
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0

    key_findings = []

    for area in analysis_doc.areas:
        severity = area.severity.severity_level

        # Count areas with actual issues (not "not_available")
        if severity != "not_available":
            areas_with_issues += 1

        if severity == "critical":
            critical_count += 1
            key_findings.append(f"{area.area}: {area.root_cause.probable_cause}")
        elif severity == "high":
            high_count += 1
            key_findings.append(f"{area.area}: {area.root_cause.probable_cause}")
        elif severity == "medium":
            medium_count += 1
        elif severity == "low":
            low_count += 1

    # Determine overall risk level
    if critical_count > 0:
        overall_risk = "Critical"
    elif high_count > 0:
        overall_risk = "High"
    elif medium_count > 0:
        overall_risk = "Medium"
    elif low_count > 0:
        overall_risk = "Low"
    else:
        overall_risk = "Not Available"

    return PropertyIssueSummary(
        total_areas_inspected=total_areas,
        areas_with_issues=areas_with_issues,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        key_findings=key_findings[:5],  # Top 5 findings
        overall_risk_level=overall_risk,
    )


def format_area_observations(analysis_doc: AnalyticalReasoningDoc) -> list[AreaObservation]:
    """
    Format area-wise observations from analytical reasoning.
    """
    observations = []

    for area in analysis_doc.areas:
        obs = AreaObservation(
            area_name=area.area,
            inspection_summary=area.inspection_summary,
            thermal_summary=area.thermal_summary,
            has_conflict=area.has_conflict,
            conflict_description=area.conflict_summary if area.has_conflict else "Not Available",
        )
        observations.append(obs)

    return observations


def extract_root_causes(analysis_doc: AnalyticalReasoningDoc) -> list[RootCauseSection]:
    """
    Extract root cause information for areas with identified issues.
    """
    root_causes = []

    for area in analysis_doc.areas:
        # Only include areas where we have a probable cause
        if area.root_cause.probable_cause != "Not Available":
            rc = RootCauseSection(
                area_name=area.area,
                probable_cause=area.root_cause.probable_cause,
                reasoning=area.root_cause.reasoning,
                confidence=area.root_cause.confidence.title(),
                supporting_evidence=area.root_cause.supporting_evidence,
                evidence_gaps=area.root_cause.evidence_gaps,
            )
            root_causes.append(rc)

    return root_causes


def extract_severity_assessments(analysis_doc: AnalyticalReasoningDoc) -> list[SeveritySection]:
    """
    Extract severity assessments for all areas.
    """
    assessments = []

    for area in analysis_doc.areas:
        if area.severity.severity_level != "not_available":
            sev = SeveritySection(
                area_name=area.area,
                severity_level=area.severity.severity_level.title(),
                reasoning=area.severity.reasoning,
                risk_factors=area.severity.risk_factors,
            )
            assessments.append(sev)

    return assessments


def generate_recommendations(analysis_doc: AnalyticalReasoningDoc) -> list[RecommendedAction]:
    """
    Generate prioritized recommended actions based on severity levels.
    """
    actions = []

    # Sort areas by severity (critical first)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "not_available": 4}

    sorted_areas = sorted(
        analysis_doc.areas, key=lambda a: severity_order.get(a.severity.severity_level, 4)
    )

    for area in sorted_areas:
        severity = area.severity.severity_level

        if severity == "critical":
            priority = "Immediate"
            action = f"Urgent investigation and remediation required for {area.area}"
            rationale = f"Critical severity: {area.severity.reasoning[:200]}..."
        elif severity == "high":
            priority = "Short-term"
            action = f"Schedule professional inspection and repair for {area.area}"
            rationale = f"High severity: {area.severity.reasoning[:200]}..."
        elif severity == "medium":
            priority = "Medium-term"
            action = f"Monitor and plan remediation for {area.area}"
            rationale = f"Medium severity: {area.severity.reasoning[:200]}..."
        elif severity == "low":
            priority = "Monitoring"
            action = f"Continue monitoring {area.area}"
            rationale = f"Low severity: {area.severity.reasoning[:200]}..."
        else:
            continue  # Skip areas without severity assessment

        actions.append(
            RecommendedAction(priority=priority, area=area.area, action=action, rationale=rationale)
        )

    return actions


def compile_missing_information(analysis_doc: AnalyticalReasoningDoc) -> list[MissingInfoSection]:
    """
    Compile missing information across all areas.
    """
    # Group missing info by category
    missing_by_category: dict[str, MissingInfoSection] = {}

    for area in analysis_doc.areas:
        for missing in area.missing_information:
            category = missing.category
            if category not in missing_by_category:
                missing_by_category[category] = MissingInfoSection(
                    category=category,
                    description=missing.description,
                    impact=missing.impact,
                    affected_areas=[area.area],
                )
            else:
                # Add this area to the affected areas list
                if area.area not in missing_by_category[category].affected_areas:
                    missing_by_category[category].affected_areas.append(area.area)

    return list(missing_by_category.values())


def generate_additional_notes(analysis_doc: AnalyticalReasoningDoc) -> list[str]:
    """
    Generate additional notes from overall missing information and metadata.
    """
    notes = []

    # Add overall missing information patterns
    if analysis_doc.overall_missing_information:
        notes.append("Cross-cutting information gaps identified:")
        for info in analysis_doc.overall_missing_information:
            notes.append(f"  - {info}")

    # Add conflict summary if any conflicts exist
    conflict_count = sum(1 for area in analysis_doc.areas if area.has_conflict)
    if conflict_count > 0:
        notes.append(
            f"\nNote: {conflict_count} area(s) have conflicts between inspection and thermal data. "
            "See Area-wise Observations for details."
        )

    # Add general recommendation
    notes.append(
        "\nThis report is based on available inspection and thermal imaging data. "
        "Additional investigation may be required for areas with insufficient evidence or missing information."
    )

    return notes


def generate_ddr_report(
    analysis_path: str | Path,
    property_name: str = "Property Inspection Report",
) -> DDRReport:
    """
    Generate a complete DDR report from analytical reasoning JSON.

    Args:
        analysis_path: Path to analytical_reasoning.json
        property_name: Name/identifier for the property

    Returns:
        DDRReport object with all sections populated
    """
    # Load analytical reasoning
    analysis_file = Path(analysis_path)
    if not analysis_file.exists():
        raise FileNotFoundError(f"Analysis file not found: {analysis_file}")

    analysis_doc = AnalyticalReasoningDoc.model_validate(
        json.loads(analysis_file.read_text(encoding="utf-8"))
    )

    # Generate all sections
    property_summary = generate_property_summary(analysis_doc)
    area_observations = format_area_observations(analysis_doc)
    root_causes = extract_root_causes(analysis_doc)
    severity_assessments = extract_severity_assessments(analysis_doc)
    recommended_actions = generate_recommendations(analysis_doc)
    missing_information = compile_missing_information(analysis_doc)
    additional_notes = generate_additional_notes(analysis_doc)

    # Create DDR report
    ddr = DDRReport(
        property_name=property_name,
        report_date=datetime.now().strftime("%Y-%m-%d"),
        property_issue_summary=property_summary,
        area_observations=area_observations,
        root_causes=root_causes,
        severity_assessments=severity_assessments,
        recommended_actions=recommended_actions,
        additional_notes=additional_notes,
        missing_information=missing_information,
    )

    return ddr
