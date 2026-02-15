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
    last_error: str | None = None
    
    for attempt in range(1, 6):  # Increased to 5 retries
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
                        f"Error: {last_error}\n"
                        f"Previous output:\n{last_text}"
                    ),
                }
            )

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            max_tokens=8000,  # Prevent truncation of large JSON responses
        )

        text = (resp.choices[0].message.content or "").strip()
        
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line if it's a code fence
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove last line if it's a code fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        
        last_text = text

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            last_error = f"JSON decode error: {str(e)}"
            print(f"Attempt {attempt}: {last_error}")
            print(f"Response preview: {text[:500]}...")
            continue

        try:
            return output_model.model_validate(data)
        except ValidationError as e:
            last_error = f"Validation error: {str(e)}"
            print(f"Attempt {attempt}: {last_error}")
            print(f"Data preview: {json.dumps(data, indent=2)[:500]}...")
            continue

    # If all retries failed, provide detailed error information
    error_msg = (
        f"Groq extraction failed to produce valid {schema_name} JSON after {attempt} retries.\n"
        f"Last error: {last_error}\n"
        f"Last response preview: {last_text[:1000] if last_text else 'None'}...\n"
        "Try reducing max_pages/chunk size or using a larger model."
    )
    raise RuntimeError(error_msg)


def extract_inspection_facts(
    *,
    chunks: list[TextChunk],
    model: str = "openai/gpt-oss-120b",
) -> InspectionFactsDoc:
    # Handle empty chunks gracefully
    if not chunks:
        print("Warning: No inspection chunks provided, returning empty InspectionFactsDoc")
        return InspectionFactsDoc(
            source="inspection_report",
            facts=[],
            missing_or_unclear_information=["No inspection data available"]
        )
    
    # Validate chunk size and split if necessary
    total_text_length = sum(len(chunk.text) for chunk in chunks)
    
    # If input is too large, process in batches
    if total_text_length > 12000:
        print(f"Warning: Inspection chunks total {total_text_length} characters. "
              f"Splitting into batches to prevent truncation.")
        
        # Split chunks into batches
        batches: list[list[TextChunk]] = []
        current_batch: list[TextChunk] = []
        current_length = 0
        
        for chunk in chunks:
            chunk_len = len(chunk.text)
            if current_batch and current_length + chunk_len > 12000:
                batches.append(current_batch)
                current_batch = [chunk]
                current_length = chunk_len
            else:
                current_batch.append(chunk)
                current_length += chunk_len
        
        if current_batch:
            batches.append(current_batch)
        
        print(f"Processing {len(batches)} batches of inspection chunks...")
        
        # Process each batch and merge results
        all_facts = []
        all_missing = []
        
        for i, batch in enumerate(batches, 1):
            print(f"Processing inspection batch {i}/{len(batches)}...")
            batch_result = _extract_inspection_facts_single(batch, model)
            all_facts.extend(batch_result.facts)
            all_missing.extend(batch_result.missing_or_unclear_information)
        
        return InspectionFactsDoc(
            source="inspection_report",
            facts=all_facts,
            missing_or_unclear_information=list(set(all_missing))  # Remove duplicates
        )
    
    # Normal processing for smaller inputs
    return _extract_inspection_facts_single(chunks, model)


def _extract_inspection_facts_single(
    chunks: list[TextChunk],
    model: str = "openai/gpt-oss-120b",
) -> InspectionFactsDoc:
    """Helper function to extract inspection facts from a single batch of chunks."""
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
    model: str = "openai/gpt-oss-120b",
) -> ThermalFactsDoc:
    # Handle empty chunks gracefully
    if not chunks:
        print("Warning: No thermal chunks provided, returning empty ThermalFactsDoc")
        return ThermalFactsDoc(
            source="thermal_report",
            facts=[],
            missing_or_unclear_information=["No thermal data available"]
        )
    
    # Validate chunk size and split if necessary
    total_text_length = sum(len(chunk.text) for chunk in chunks)
    
    # If input is too large, process in batches
    if total_text_length > 12000:
        print(f"Warning: Thermal chunks total {total_text_length} characters. "
              f"Splitting into batches to prevent truncation.")
        
        # Split chunks into batches
        batches: list[list[TextChunk]] = []
        current_batch: list[TextChunk] = []
        current_length = 0
        
        for chunk in chunks:
            chunk_len = len(chunk.text)
            if current_batch and current_length + chunk_len > 12000:
                batches.append(current_batch)
                current_batch = [chunk]
                current_length = chunk_len
            else:
                current_batch.append(chunk)
                current_length += chunk_len
        
        if current_batch:
            batches.append(current_batch)
        
        print(f"Processing {len(batches)} batches of thermal chunks...")
        
        # Process each batch and merge results
        all_facts = []
        all_missing = []
        
        for i, batch in enumerate(batches, 1):
            print(f"Processing thermal batch {i}/{len(batches)}...")
            batch_result = _extract_thermal_facts_single(batch, model)
            all_facts.extend(batch_result.facts)
            all_missing.extend(batch_result.missing_or_unclear_information)
        
        return ThermalFactsDoc(
            source="thermal_report",
            facts=all_facts,
            missing_or_unclear_information=list(set(all_missing))  # Remove duplicates
        )
    
    # Normal processing for smaller inputs
    return _extract_thermal_facts_single(chunks, model)


def _extract_thermal_facts_single(
    chunks: list[TextChunk],
    model: str = "openai/gpt-oss-120b",
) -> ThermalFactsDoc:
    """Helper function to extract thermal facts from a single batch of chunks."""
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

