from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from groq import Groq

from ..step2.merge_layer import MergedAreaDataDoc, MergedAreaEntry
from .models import (
    AnalyticalReasoningDoc,
    AreaAnalysis,
    MissingInformation,
    RootCauseInference,
    SeverityAssessment,
)


def build_reasoning_prompt(area_entry: MergedAreaEntry) -> str:
    """
    Build a structured prompt for the LLM with strict constraints.
    The prompt explicitly instructs the model to only use provided facts.
    """

    # Serialize inspection facts
    inspection_facts_text = "NONE"
    if area_entry.inspection_facts:
        inspection_items = []
        for idx, fact in enumerate(area_entry.inspection_facts, 1):
            items = [
                f"  Observation: {fact.observation}",
                f"  Visible Issue: {fact.visible_issue}",
                f"  Moisture Signs: {fact.moisture_signs}",
                f"  Notes: {fact.notes}",
                f"  Evidence: Pages {fact.evidence.page_numbers}, Quote: \"{fact.evidence.quote}\"",
            ]
            inspection_items.append(f"Inspection Fact #{idx}:\n" + "\n".join(items))
        inspection_facts_text = "\n\n".join(inspection_items)

    # Serialize thermal facts
    thermal_facts_text = "NONE"
    if area_entry.thermal_facts:
        thermal_items = []
        for idx, fact in enumerate(area_entry.thermal_facts, 1):
            temps = []
            for t in fact.temperature_readings:
                if t.label != "Not Available" or t.value != "Not Available":
                    temps.append(f"{t.label}: {t.value}")
            temp_text = ", ".join(temps) if temps else "Not Available"

            items = [
                f"  Thermal Anomaly: {fact.thermal_anomaly}",
                f"  Temperature Readings: {temp_text}",
                f"  Suspected Issue: {fact.suspected_issue}",
                f"  Notes: {fact.notes}",
                f"  Evidence: Pages {fact.evidence.page_numbers}, Quote: \"{fact.evidence.quote}\"",
            ]
            thermal_items.append(f"Thermal Fact #{idx}:\n" + "\n".join(items))
        thermal_facts_text = "\n\n".join(thermal_items)

    # Serialize conflicts
    conflicts_text = "NONE"
    if area_entry.conflicts:
        conflict_items = []
        for idx, conflict in enumerate(area_entry.conflicts, 1):
            items = [
                f"  Type: {conflict.type}",
                f"  Inspection Statement: {conflict.inspection_statement}",
                f"  Thermal Statement: {conflict.thermal_statement}",
            ]
            conflict_items.append(f"Conflict #{idx}:\n" + "\n".join(items))
        conflicts_text = "\n\n".join(conflict_items)

    prompt = f"""You are an analytical reasoning assistant for building inspection reports. Your task is to analyze the provided structured data for a specific area and produce a JSON response with root cause inference, severity assessment, and missing information identification.

CRITICAL CONSTRAINTS:
1. You may ONLY reference facts explicitly provided in the data below
2. If evidence is insufficient to make a determination, you MUST use "Not Available" or "insufficient_evidence"
3. You MUST cite specific evidence (page numbers, quotes) for all inferences
4. You MUST NOT invent, assume, or hallucinate any information
5. If information conflicts, acknowledge the conflict and explain both sides

AREA: {area_entry.area}

INSPECTION FACTS:
{inspection_facts_text}

THERMAL FACTS:
{thermal_facts_text}

CONFLICTS DETECTED:
{conflicts_text}

YOUR TASK:
Analyze the above data and produce a JSON response with the following structure:

{{
  "root_cause": {{
    "probable_cause": "string (describe the most likely root cause, or 'Not Available')",
    "reasoning": "string (explain your reasoning based on evidence, or 'Not Available')",
    "supporting_evidence": ["list of specific quotes or page references"],
    "confidence": "high|medium|low|insufficient_evidence",
    "evidence_gaps": ["list what additional info would help"]
  }},
  "severity": {{
    "severity_level": "critical|high|medium|low|not_available",
    "reasoning": "string (explain why this severity level, or 'Not Available')",
    "risk_factors": ["list specific factors from the data"],
    "supporting_evidence": ["list of specific quotes or page references"]
  }},
  "missing_information": [
    {{
      "category": "string (e.g., 'moisture measurements', 'structural details')",
      "description": "string (what specific information is missing)",
      "impact": "string (how this affects the analysis)"
    }}
  ],
  "inspection_summary": "string (brief summary of inspection findings, or 'Not Available')",
  "thermal_summary": "string (brief summary of thermal findings, or 'Not Available')",
  "conflict_summary": "string (if conflicts exist, summarize them, otherwise 'Not Available')"
}}

EXAMPLES OF PROPER REASONING:

Good (evidence-based):
- "probable_cause": "Potential water intrusion from exterior wall", "reasoning": "Inspection report notes visible moisture signs on bedroom wall (page 3), and thermal imaging shows temperature anomaly consistent with moisture (page 2, hotspot 15.2°C vs ambient 18.5°C)", "confidence": "medium"

Bad (hallucination):
- "probable_cause": "Broken pipe in the wall" (NO - there's no evidence of a pipe)

Good (insufficient evidence):
- "probable_cause": "Not Available", "reasoning": "Inspection notes moisture signs but no thermal data available for this area, and no structural inspection was performed", "confidence": "insufficient_evidence"

Now analyze the data and respond with ONLY valid JSON, no other text:"""

    return prompt


def parse_llm_response(response_text: str, area_name: str) -> AreaAnalysis:
    """
    Parse and validate the LLM's JSON response into an AreaAnalysis model.
    """
    try:
        data = json.loads(response_text)

        # Build root cause inference
        root_cause_data = data.get("root_cause", {})
        root_cause = RootCauseInference(
            probable_cause=root_cause_data.get("probable_cause", "Not Available"),
            reasoning=root_cause_data.get("reasoning", "Not Available"),
            supporting_evidence=root_cause_data.get("supporting_evidence", []),
            confidence=root_cause_data.get("confidence", "insufficient_evidence"),
            evidence_gaps=root_cause_data.get("evidence_gaps", []),
        )

        # Build severity assessment
        severity_data = data.get("severity", {})
        severity = SeverityAssessment(
            severity_level=severity_data.get("severity_level", "not_available"),
            reasoning=severity_data.get("reasoning", "Not Available"),
            risk_factors=severity_data.get("risk_factors", []),
            supporting_evidence=severity_data.get("supporting_evidence", []),
        )

        # Build missing information list
        missing_info = []
        for item in data.get("missing_information", []):
            missing_info.append(
                MissingInformation(
                    category=item.get("category", "Not Available"),
                    description=item.get("description", "Not Available"),
                    impact=item.get("impact", "Not Available"),
                )
            )

        # Build area analysis
        area_analysis = AreaAnalysis(
            area=area_name,
            has_conflict=data.get("has_conflict", False),
            conflict_summary=data.get("conflict_summary", "Not Available"),
            root_cause=root_cause,
            severity=severity,
            missing_information=missing_info,
            inspection_summary=data.get("inspection_summary", "Not Available"),
            thermal_summary=data.get("thermal_summary", "Not Available"),
        )

        return area_analysis

    except json.JSONDecodeError as e:
        # Fallback if JSON parsing fails
        return AreaAnalysis(
            area=area_name,
            root_cause=RootCauseInference(
                probable_cause="Not Available",
                reasoning=f"Failed to parse LLM response: {str(e)}",
                confidence="insufficient_evidence",
            ),
            severity=SeverityAssessment(severity_level="not_available"),
        )


def call_groq_reasoning(prompt: str, model: str = "openai/gpt-oss-120b") -> str:
    """
    Call Groq API for reasoning with retry logic.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")

    client = Groq(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise analytical assistant that only uses provided evidence and never invents information. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Low temperature for more deterministic reasoning
            max_tokens=2000,
            response_format={"type": "json_object"},  # Force JSON output
        )

        return response.choices[0].message.content or "{}"

    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return "{}"


def analyze_area(area_entry: MergedAreaEntry) -> AreaAnalysis:
    """
    Analyze a single area using controlled LLM reasoning.
    """
    print(f"  Analyzing area: {area_entry.area}")

    # Build prompt
    prompt = build_reasoning_prompt(area_entry)

    # Call LLM
    response_text = call_groq_reasoning(prompt)

    # Parse response
    area_analysis = parse_llm_response(response_text, area_entry.area)

    # Set conflict flag from merged data
    area_analysis.has_conflict = area_entry.conflict_detected
    if area_entry.conflict_detected and area_entry.conflicts:
        conflict_summaries = [
            f"{c.type}: {c.inspection_statement} vs {c.thermal_statement}" for c in area_entry.conflicts
        ]
        area_analysis.conflict_summary = "; ".join(conflict_summaries)

    return area_analysis


def run_analytical_reasoning(
    merged_data_path: str | Path,
    out_dir: str | Path,
) -> Path:
    """
    Main orchestration function for Step 3 analytical reasoning.

    Args:
        merged_data_path: Path to merged_area_data.json
        out_dir: Output directory for analytical_reasoning.json

    Returns:
        Path to the output file
    """
    print("Starting Step 3: Analytical Reasoning Layer")
    print(f"Input: {merged_data_path}")

    # Load merged data
    merged_path = Path(merged_data_path)
    if not merged_path.exists():
        raise FileNotFoundError(f"Merged data file not found: {merged_path}")

    merged_data = MergedAreaDataDoc.model_validate(json.loads(merged_path.read_text(encoding="utf-8")))

    print(f"Loaded {len(merged_data.merged_areas)} areas to analyze")

    # Analyze each area
    area_analyses = []
    for area_entry in merged_data.merged_areas:
        area_analysis = analyze_area(area_entry)
        area_analyses.append(area_analysis)

    # Identify overall missing information patterns
    overall_missing = []
    missing_categories = {}
    for analysis in area_analyses:
        for missing in analysis.missing_information:
            cat = missing.category
            if cat not in missing_categories:
                missing_categories[cat] = []
            missing_categories[cat].append(missing.description)

    # If a category appears in multiple areas, it's a cross-cutting issue
    for category, descriptions in missing_categories.items():
        if len(descriptions) >= 2:  # Appears in 2+ areas
            overall_missing.append(f"{category}: affects {len(descriptions)} areas")

    # Build final document
    reasoning_doc = AnalyticalReasoningDoc(
        areas=area_analyses,
        overall_missing_information=overall_missing,
        analysis_metadata={
            "timestamp": datetime.now().isoformat(),
            "model": "openai/gpt-oss-120b",
            "input_file": str(merged_path),
            "areas_analyzed": str(len(area_analyses)),
        },
    )

    # Write output
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / "analytical_reasoning.json"
    out_file.write_text(reasoning_doc.model_dump_json(indent=2), encoding="utf-8")

    print(f"\nAnalysis complete!")
    print(f"Output written to: {out_file}")
    print(f"Areas analyzed: {len(area_analyses)}")

    # Print summary
    critical_count = sum(1 for a in area_analyses if a.severity.severity_level == "critical")
    high_count = sum(1 for a in area_analyses if a.severity.severity_level == "high")
    medium_count = sum(1 for a in area_analyses if a.severity.severity_level == "medium")

    print(f"\nSeverity Summary:")
    print(f"  Critical: {critical_count}")
    print(f"  High: {high_count}")
    print(f"  Medium: {medium_count}")

    return out_file
