from __future__ import annotations

import json
import os
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from .chunking import TextChunk
from .models import InspectionFactsDoc, ThermalFactsDoc

T = TypeVar("T", bound=BaseModel)


def _chunks_to_prompt(chunks: list[TextChunk]) -> str:
    # Keep provenance: each chunk shows its page numbers.
    parts: list[str] = []
    for i, ch in enumerate(chunks, start=1):
        parts.append(f"[CHUNK {i} | pages={ch.page_numbers}]\n{ch.text}")
    return "\n\n".join(parts).strip()


def _call_openai_json_schema(*, model: str, schema: dict[str, Any], prompt: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in your environment to run Step 2 extraction."
        )

    client = OpenAI(api_key=api_key)

    resp = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You extract facts from inspection/thermal text. "
                    "Return ONLY valid JSON that matches the provided schema. "
                    "Do not invent facts. If missing, use 'Not Available'."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "facts_extraction",
                "schema": schema,
                "strict": True,
            },
        },
    )

    text = resp.output_text
    return json.loads(text)


def extract_inspection_facts(
    *,
    chunks: list[TextChunk],
    model: str = "gpt-4.1-mini",
) -> InspectionFactsDoc:
    schema = InspectionFactsDoc.model_json_schema()

    prompt = (
        "Extract inspection facts into the schema.\n\n"
        "Rules:\n"
        "- Do NOT invent facts.\n"
        "- If a field is not present, output 'Not Available'.\n"
        "- Use simple, short values.\n"
        "- Populate evidence.page_numbers using the chunk pages where you found the info.\n"
        "- evidence.quote must be an exact short quote from the text (or 'Not Available').\n\n"
        "TEXT:\n" + _chunks_to_prompt(chunks)
    )

    data = _call_openai_json_schema(model=model, schema=schema, prompt=prompt)
    return InspectionFactsDoc.model_validate(data)


def extract_thermal_facts(
    *,
    chunks: list[TextChunk],
    model: str = "gpt-4.1-mini",
) -> ThermalFactsDoc:
    schema = ThermalFactsDoc.model_json_schema()

    prompt = (
        "Extract thermal facts into the schema.\n\n"
        "Rules:\n"
        "- Do NOT interpret thermal images. Only use printed labels/text values.\n"
        "- Do NOT invent facts.\n"
        "- If a field is not present, output 'Not Available'.\n"
        "- Put temperatures as strings exactly as seen (e.g., '25.7 °C').\n"
        "- Populate evidence.page_numbers and evidence.quote from the text.\n\n"
        "TEXT:\n" + _chunks_to_prompt(chunks)
    )

    data = _call_openai_json_schema(model=model, schema=schema, prompt=prompt)
    return ThermalFactsDoc.model_validate(data)
