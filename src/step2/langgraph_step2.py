from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from src.input_layer.types import InputLayerOutput

from .chunking import TextChunk, chunk_pages
from .models import InspectionFactsDoc, ThermalFactsDoc
from .groq_extract import extract_inspection_facts, extract_thermal_facts
from .preprocess import combine_raw_and_ocr, remove_common_boilerplate


class Step2State(TypedDict, total=False):
    input_json_path: str
    out_dir: str

    # If false, run only deterministic preprocessing (chunks) and stop.
    run_llm: bool

    inspection_chunks: list[TextChunk]
    thermal_chunks: list[TextChunk]

    inspection_facts: InspectionFactsDoc
    thermal_facts: ThermalFactsDoc


def build_step2_graph() -> StateGraph:
    g = StateGraph(Step2State)

    def preprocess_node(state: Step2State) -> Step2State:
        input_path = Path(state["input_json_path"])
        out_dir = Path(state["out_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)

        data = json.loads(input_path.read_text(encoding="utf-8"))
        parsed = InputLayerOutput.model_validate(data)

        inspection_chunks: list[TextChunk] = []
        thermal_chunks: list[TextChunk] = []

        if parsed.inspection is not None:
            combined_pages = [
                (p.page_number, combine_raw_and_ocr(p.raw_text, p.ocr_text))
                for p in parsed.inspection.pages
            ]
            # Remove boilerplate across the inspection document
            cleaned_texts = remove_common_boilerplate([t for _, t in combined_pages])
            combined_pages = [(combined_pages[i][0], cleaned_texts[i]) for i in range(len(combined_pages))]
            inspection_chunks = chunk_pages(source="inspection_report", pages=combined_pages)

        if parsed.thermal is not None:
            combined_pages = [
                (p.page_number, combine_raw_and_ocr(p.raw_text, p.ocr_text))
                for p in parsed.thermal.pages
            ]
            cleaned_texts = remove_common_boilerplate([t for _, t in combined_pages])
            combined_pages = [(combined_pages[i][0], cleaned_texts[i]) for i in range(len(combined_pages))]
            thermal_chunks = chunk_pages(source="thermal_report", pages=combined_pages)

        # Save deterministic outputs
        (out_dir / "inspection_chunks.json").write_text(
            json.dumps([c.__dict__ for c in inspection_chunks], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (out_dir / "thermal_chunks.json").write_text(
            json.dumps([c.__dict__ for c in thermal_chunks], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return {
            "inspection_chunks": inspection_chunks,
            "thermal_chunks": thermal_chunks,
        }

    def extract_node(state: Step2State) -> Step2State:
        out_dir = Path(state["out_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)

        inspection_facts = extract_inspection_facts(chunks=state.get("inspection_chunks", []))
        thermal_facts = extract_thermal_facts(chunks=state.get("thermal_chunks", []))

        (out_dir / "inspection_facts.json").write_text(
            inspection_facts.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (out_dir / "thermal_facts.json").write_text(
            thermal_facts.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return {"inspection_facts": inspection_facts, "thermal_facts": thermal_facts}

    g.add_node("preprocess", preprocess_node)
    g.add_node("extract", extract_node)

    g.set_entry_point("preprocess")

    def _route_after_preprocess(state: Step2State) -> str:
        if state.get("run_llm", True):
            return "extract"
        return END

    g.add_conditional_edges("preprocess", _route_after_preprocess)
    g.add_edge("extract", END)

    return g


def run_step2(
    *,
    input_json_path: str,
    out_dir: str,
    run_llm: bool = True,
) -> None:
    graph = build_step2_graph().compile()
    graph.invoke({"input_json_path": input_json_path, "out_dir": out_dir, "run_llm": run_llm})
