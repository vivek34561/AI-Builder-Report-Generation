from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from .config import InputLayerConfig
from .extract import extract_document
from .types import DocumentExtraction, InputLayerOutput


class InputState(TypedDict, total=False):
    inspection_pdf: str
    thermal_pdf: str
    out_dir: str
    config: InputLayerConfig

    inspection: DocumentExtraction
    thermal: DocumentExtraction

    output_json_path: str


def _doc_to_audit_text(doc: DocumentExtraction) -> str:
    parts: list[str] = []
    parts.append(f"source: {doc.source}")
    parts.append(f"pdf_path: {doc.pdf_path}")
    parts.append("")

    for page in doc.pages:
        parts.append("=" * 80)
        parts.append(f"PAGE {page.page_number}")
        parts.append(f"page_image_path: {page.page_image_path or ''}")
        parts.append("")

        parts.append("[raw_text]")
        parts.append(page.raw_text.strip() if page.raw_text.strip() else "(empty)")
        parts.append("")

        parts.append("[ocr_text]")
        parts.append(page.ocr_text.strip() if page.ocr_text.strip() else "(empty)")
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def build_input_layer_graph() -> StateGraph:
    g = StateGraph(InputState)

    def extract_inspection_node(state: InputState) -> InputState:
        doc = extract_document(
            pdf_path=state["inspection_pdf"],
            source="inspection_report",
            out_dir=state["out_dir"],
            config=state["config"],
        )
        return {"inspection": doc}

    def extract_thermal_node(state: InputState) -> InputState:
        doc = extract_document(
            pdf_path=state["thermal_pdf"],
            source="thermal_report",
            out_dir=state["out_dir"],
            config=state["config"],
        )
        return {"thermal": doc}

    def write_output_node(state: InputState) -> InputState:
        out_dir = Path(state["out_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        output = InputLayerOutput(
            inspection=state.get("inspection"),
            thermal=state.get("thermal"),
        )
        out_path = out_dir / "input_layer_output.json"
        out_path.write_text(json.dumps(output.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

        # Convenience audit text files (no inference; just concatenation of extracted text).
        inspection = state.get("inspection")
        thermal = state.get("thermal")
        if inspection is not None:
            (out_dir / "inspection.txt").write_text(_doc_to_audit_text(inspection), encoding="utf-8")
        if thermal is not None:
            (out_dir / "thermal.txt").write_text(_doc_to_audit_text(thermal), encoding="utf-8")
        return {"output_json_path": str(out_path)}

    g.add_node("extract_inspection", extract_inspection_node)
    g.add_node("extract_thermal", extract_thermal_node)
    g.add_node("write_output", write_output_node)

    g.set_entry_point("extract_inspection")
    g.add_edge("extract_inspection", "extract_thermal")
    g.add_edge("extract_thermal", "write_output")
    g.add_edge("write_output", END)

    return g


def run_input_layer(
    *,
    inspection_pdf: str,
    thermal_pdf: str,
    out_dir: str,
    config: Optional[InputLayerConfig] = None,
) -> str:
    config = config or InputLayerConfig()
    graph = build_input_layer_graph().compile()

    final_state = graph.invoke(
        {
            "inspection_pdf": inspection_pdf,
            "thermal_pdf": thermal_pdf,
            "out_dir": out_dir,
            "config": config,
        }
    )
    return final_state["output_json_path"]
