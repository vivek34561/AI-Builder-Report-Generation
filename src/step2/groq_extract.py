from __future__ import annotations

import json
import os
from typing import TypeVar

from groq import Groq
from pydantic import BaseModel, ValidationError

from .chunking import TextChunk
from .models import InspectionFactsDoc, ThermalFactsDoc

T = TypeVar("T", bound=BaseModel)


def _chunks_to_prompt(chunks: list[TextChunk]) -> str:
    parts: list[str] = []
    for i, ch in enumerate(chunks, start=1):
        parts.append(f"[CHUNK {i} | pages={ch.page_numbers}]\n{ch.text}")
    return "\n\n".join(parts).strip()


def _extract_with_retries(*, model: str, prompt: str, schema_name: str, output_model: type[T]) -> T:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Set it in your environment to run Step 2 extraction."
        )

    client = Groq(api_key=api_key)

    last_text: str | None = None
    for attempt in range(1, 4):
        messages = [
            {
                "role": "system",
                "content": (
                    "You extract facts from inspection/thermal text. "
                    "Return ONLY valid JSON. Do not add markdown, code fences, or commentary. "
                    "Do not invent facts. If missing, use 'Not Available'."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        if last_text:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous output did not validate. "
                        "Fix it to be valid JSON matching the schema exactly. "
                        f"Previous output:\n{last_text}"
                    ),
                }
            )

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
        )

        text = (resp.choices[0].message.content or "").strip()
        last_text = text

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue

        try:
            return output_model.model_validate(data)
        except ValidationError:
            continue

    raise RuntimeError(
        f"Groq extraction failed to produce valid {schema_name} JSON after retries. "
        "Try reducing max_pages/chunk size or using a larger model."
    )


def extract_inspection_facts(
    *,
    chunks: list[TextChunk],
    model: str = "llama-3.1-70b-versatile",
) -> InspectionFactsDoc:
    schema = InspectionFactsDoc.model_json_schema()

    prompt = (
        "Extract inspection facts into the provided JSON schema.\n\n"
        "Rules:\n"
        "- Do NOT invent facts.\n"
        "- If a field is not present, output 'Not Available'.\n"
        "- Use short, client-friendly text.\n"
        "- evidence.page_numbers must reference the chunk pages you used.\n"
        "- evidence.quote must be an exact short quote from the text (or 'Not Available').\n\n"
        "JSON SCHEMA (must match):\n"
        + json.dumps(schema, indent=2)
        + "\n\nTEXT:\n"
        + _chunks_to_prompt(chunks)
    )

    return _extract_with_retries(
        model=model,
        prompt=prompt,
        schema_name="InspectionFactsDoc",
        output_model=InspectionFactsDoc,
    )


def extract_thermal_facts(
    *,
    chunks: list[TextChunk],
    model: str = "llama-3.1-70b-versatile",
) -> ThermalFactsDoc:
    schema = ThermalFactsDoc.model_json_schema()

    prompt = (
        "Extract thermal facts into the provided JSON schema.\n\n"
        "Rules:\n"
        "- Do NOT interpret thermal images. Only use printed labels/text values.\n"
        "- Do NOT invent facts.\n"
        "- If a field is not present, output 'Not Available'.\n"
        "- Put temperatures as strings exactly as seen (e.g., '25.7 °C').\n"
        "- evidence.page_numbers and evidence.quote must come from the text.\n\n"
        "JSON SCHEMA (must match):\n"
        + json.dumps(schema, indent=2)
        + "\n\nTEXT:\n"
        + _chunks_to_prompt(chunks)
    )

    return _extract_with_retries(
        model=model,
        prompt=prompt,
        schema_name="ThermalFactsDoc",
        output_model=ThermalFactsDoc,
    )
