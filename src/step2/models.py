from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


MoistureSigns = Literal["yes", "no", "not_mentioned"]


class Evidence(BaseModel):
    page_numbers: list[int] = Field(default_factory=list)
    quote: str = "Not Available"


class Measurement(BaseModel):
    name: str = "Not Available"
    value: str = "Not Available"


class InspectionFact(BaseModel):
    area: str = "Not Available"
    observation: str = "Not Available"
    visible_issue: str = "Not Available"
    moisture_signs: MoistureSigns = "not_mentioned"
    measurements: list[Measurement] = Field(default_factory=list)
    notes: str = "Not Available"
    evidence: Evidence = Field(default_factory=Evidence)


class TemperatureReading(BaseModel):
    label: str = "Not Available"  # e.g., Hotspot, Coldspot
    value: str = "Not Available"  # keep as string, do not convert


class ThermalFact(BaseModel):
    area: str = "Not Available"
    thermal_anomaly: Literal["yes", "no", "not_mentioned"] = "not_mentioned"
    temperature_readings: list[TemperatureReading] = Field(default_factory=list)
    suspected_issue: str = "Not Available"
    notes: str = "Not Available"
    evidence: Evidence = Field(default_factory=Evidence)


class InspectionFactsDoc(BaseModel):
    source: Literal["inspection_report"] = "inspection_report"
    facts: list[InspectionFact] = Field(default_factory=list)
    missing_or_unclear_information: list[str] = Field(default_factory=list)


class ThermalFactsDoc(BaseModel):
    source: Literal["thermal_report"] = "thermal_report"
    facts: list[ThermalFact] = Field(default_factory=list)
    missing_or_unclear_information: list[str] = Field(default_factory=list)
