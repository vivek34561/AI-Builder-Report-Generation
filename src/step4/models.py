from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PropertyIssueSummary(BaseModel):
    """High-level overview of all identified issues across the property."""

    total_areas_inspected: int = 0
    areas_with_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    key_findings: list[str] = Field(default_factory=list)
    overall_risk_level: Literal["Critical", "High", "Medium", "Low", "Not Available"] = "Not Available"


class AreaObservation(BaseModel):
    """Detailed observations for a single area."""

    area_name: str = "Not Available"
    inspection_summary: str = "Not Available"
    thermal_summary: str = "Not Available"
    has_conflict: bool = False
    conflict_description: str = "Not Available"


class RootCauseSection(BaseModel):
    """Root cause information for an area."""

    area_name: str = "Not Available"
    probable_cause: str = "Not Available"
    reasoning: str = "Not Available"
    confidence: str = "Not Available"
    supporting_evidence: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)


class SeveritySection(BaseModel):
    """Severity assessment for an area."""

    area_name: str = "Not Available"
    severity_level: str = "Not Available"
    reasoning: str = "Not Available"
    risk_factors: list[str] = Field(default_factory=list)


class RecommendedAction(BaseModel):
    """A single recommended action with priority."""

    priority: Literal["Immediate", "Short-term", "Medium-term", "Monitoring"] = "Monitoring"
    area: str = "Not Available"
    action: str = "Not Available"
    rationale: str = "Not Available"


class MissingInfoSection(BaseModel):
    """Missing or unclear information."""

    category: str = "Not Available"
    description: str = "Not Available"
    impact: str = "Not Available"
    affected_areas: list[str] = Field(default_factory=list)


class DDRReport(BaseModel):
    """
    Complete Detailed Diagnostic Report (DDR) structure.
    Matches the exact sections required by the assignment.
    """

    # Metadata
    property_name: str = "Property Inspection Report"
    report_date: str = "Not Available"

    # Required sections (in order)
    property_issue_summary: PropertyIssueSummary = Field(default_factory=PropertyIssueSummary)
    area_observations: list[AreaObservation] = Field(default_factory=list)
    root_causes: list[RootCauseSection] = Field(default_factory=list)
    severity_assessments: list[SeveritySection] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    additional_notes: list[str] = Field(default_factory=list)
    missing_information: list[MissingInfoSection] = Field(default_factory=list)
