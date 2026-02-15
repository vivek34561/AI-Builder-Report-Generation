from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RootCauseInference(BaseModel):
    """
    Inferred probable root cause based on available evidence.
    Must cite specific evidence and indicate confidence level.
    """

    probable_cause: str = "Not Available"
    reasoning: str = "Not Available"
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="Specific quotes or page references from the source data",
    )
    confidence: Literal["high", "medium", "low", "insufficient_evidence"] = "insufficient_evidence"
    evidence_gaps: list[str] = Field(
        default_factory=list,
        description="What additional information would strengthen this inference",
    )


class SeverityAssessment(BaseModel):
    """
    Severity rating with clear reasoning based on evidence.
    Must explain why this severity level was assigned.
    """

    severity_level: Literal["critical", "high", "medium", "low", "not_available"] = "not_available"
    reasoning: str = "Not Available"
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Specific factors that influenced severity rating",
    )
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="Evidence supporting this severity assessment",
    )


class MissingInformation(BaseModel):
    """
    Explicitly identified gaps or unclear information in the data.
    """

    category: str = "Not Available"
    description: str = "Not Available"
    impact: str = "Not Available"  # How this missing info affects analysis


class AreaAnalysis(BaseModel):
    """
    Complete analytical reasoning for a single area.
    All fields must be evidence-based or marked "Not Available".
    """

    area: str = "Not Available"
    has_conflict: bool = False
    conflict_summary: str = "Not Available"

    # Core analysis
    root_cause: RootCauseInference = Field(default_factory=RootCauseInference)
    severity: SeverityAssessment = Field(default_factory=SeverityAssessment)

    # Data quality
    missing_information: list[MissingInformation] = Field(default_factory=list)

    # Summary of available facts (for transparency)
    inspection_summary: str = "Not Available"
    thermal_summary: str = "Not Available"


class AnalyticalReasoningDoc(BaseModel):
    """
    Top-level document containing analytical reasoning for all areas.
    This is the output of Step 3.
    """

    areas: list[AreaAnalysis] = Field(default_factory=list)
    overall_missing_information: list[str] = Field(
        default_factory=list,
        description="Cross-cutting information gaps affecting multiple areas",
    )
    analysis_metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Metadata about the analysis (timestamp, model used, etc.)",
    )
