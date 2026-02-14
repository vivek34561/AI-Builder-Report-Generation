from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class OCRSpan(BaseModel):
    text: str
    confidence: float | None = None


class PageExtraction(BaseModel):
    source: Literal["inspection_report", "thermal_report"]
    pdf_path: str
    page_number: int = Field(..., description="1-based")

    raw_text: str = ""
    ocr_text: str = ""
    ocr_spans: list[OCRSpan] = Field(default_factory=list)

    page_image_path: str | None = None

    # A place to store minimally structured fields (no inference)
    fields: dict[str, Any] = Field(default_factory=dict)


class DocumentExtraction(BaseModel):
    source: Literal["inspection_report", "thermal_report"]
    pdf_path: str
    pages: list[PageExtraction]


class InputLayerOutput(BaseModel):
    inspection: DocumentExtraction | None = None
    thermal: DocumentExtraction | None = None
