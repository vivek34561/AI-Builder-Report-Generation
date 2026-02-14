from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field

from .models import Evidence, InspectionFact, InspectionFactsDoc, ThermalFact, ThermalFactsDoc


class MergeConflict(BaseModel):
    type: str = "Not Available"
    inspection_statement: str = "Not Available"
    thermal_statement: str = "Not Available"
    inspection_evidence: Evidence = Field(default_factory=Evidence)
    thermal_evidence: Evidence = Field(default_factory=Evidence)
    conflict_detected: bool = True


class MergedAreaEntry(BaseModel):
    area: str = "Not Available"
    inspection_facts: list[InspectionFact] = Field(default_factory=list)
    thermal_facts: list[ThermalFact] = Field(default_factory=list)
    conflicts: list[MergeConflict] = Field(default_factory=list)
    conflict_detected: bool = False


class MergedAreaDataDoc(BaseModel):
    merged_areas: list[MergedAreaEntry] = Field(default_factory=list)


_WS_RE = re.compile(r"\s+")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_PUNCT_RE = re.compile(r"[^\w\s]")


def _normalize_area(area: str) -> str:
    area = (area or "").strip()
    if not area or area.lower() == "not available":
        return "not_available"
    area = _CTRL_RE.sub(" ", area)
    area = _WS_RE.sub(" ", area)
    return area.casefold()


def _normalize_text_for_match(text: str) -> str:
    text = (text or "").strip()
    if not text or text.lower() == "not available":
        return ""
    text = _CTRL_RE.sub(" ", text)
    text = text.casefold()
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _similar(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _inspection_statement(f: InspectionFact) -> str:
    parts: list[str] = []
    if f.observation and f.observation != "Not Available":
        parts.append(f.observation)
    if f.visible_issue and f.visible_issue != "Not Available":
        parts.append(f.visible_issue)
    if f.moisture_signs and f.moisture_signs != "not_mentioned":
        parts.append(f"moisture_signs={f.moisture_signs}")
    if f.notes and f.notes != "Not Available":
        parts.append(f.notes)
    return " | ".join(parts) if parts else "Not Available"


def _thermal_statement(f: ThermalFact) -> str:
    parts: list[str] = []
    if f.suspected_issue and f.suspected_issue != "Not Available":
        parts.append(f.suspected_issue)
    if f.thermal_anomaly and f.thermal_anomaly != "not_mentioned":
        parts.append(f"thermal_anomaly={f.thermal_anomaly}")
    temps = [
        f"{t.label}:{t.value}"
        for t in (f.temperature_readings or [])
        if (t.label and t.label != "Not Available") or (t.value and t.value != "Not Available")
    ]
    if temps:
        parts.append("temps=" + "; ".join(temps))
    if f.notes and f.notes != "Not Available":
        parts.append(f.notes)
    return " | ".join(parts) if parts else "Not Available"


@dataclass(frozen=True)
class _DedupeConfig:
    similarity_threshold: float = 0.92


def _dedupe_facts(
    facts: Iterable[BaseModel],
    *,
    statement_fn,
    cfg: _DedupeConfig,
) -> list:
    kept: list = []
    kept_sigs: list[str] = []

    for f in facts:
        stmt = statement_fn(f)
        sig = _normalize_text_for_match(stmt)

        if not sig:
            kept.append(f)
            kept_sigs.append(sig)
            continue

        is_dup = False

        for existing_sig in kept_sigs:
            if not existing_sig:
                continue
            if sig == existing_sig:
                is_dup = True
                break
            if _similar(sig, existing_sig) >= cfg.similarity_threshold:
                is_dup = True
                break

        if not is_dup:
            kept.append(f)
            kept_sigs.append(sig)

    return kept


_NEG_MOISTURE_PATTERNS = (
    "no damp",
    "no moisture",
    "no leak",
    "no leakage",
    "no water",
    "dry",
    "not damp",
    "not wet",
    "no sign of moisture",
)

_POS_MOISTURE_PATTERNS = (
    "moisture",
    "damp",
    "wet",
    "leak",
    "leakage",
    "water intrusion",
    "water ingress",
    "condensation",
)


def _mentions_any(text: str, patterns: tuple[str, ...]) -> bool:
    norm = _normalize_text_for_match(text)
    return any(p in norm for p in patterns)


def _inspection_indicates_no_moisture(f: InspectionFact) -> bool:
    if f.moisture_signs == "no":
        return True
    stmt = _inspection_statement(f)
    return _mentions_any(stmt, _NEG_MOISTURE_PATTERNS)


def _thermal_indicates_moisture_anomaly(f: ThermalFact) -> bool:
    if f.thermal_anomaly == "yes" and _mentions_any(f.suspected_issue or "", _POS_MOISTURE_PATTERNS):
        return True
    stmt = _thermal_statement(f)
    return _mentions_any(stmt, _POS_MOISTURE_PATTERNS) and f.thermal_anomaly == "yes"


def merge_and_dedupe(
    *,
    inspection: InspectionFactsDoc | None,
    thermal: ThermalFactsDoc | None,
    similarity_threshold: float = 0.92,
) -> MergedAreaDataDoc:
    cfg = _DedupeConfig(similarity_threshold=similarity_threshold)

    area_map: dict[str, MergedAreaEntry] = {}
    area_display: dict[str, str] = {}

    def ensure_area(area_raw: str) -> MergedAreaEntry:
        key = _normalize_area(area_raw)
        if key not in area_map:
            display = (area_raw or "").strip() or "Not Available"
            if display.lower() == "not available":
                display = "Not Available"
            area_display[key] = display
            area_map[key] = MergedAreaEntry(area=display)
        return area_map[key]

    if inspection is not None:
        for f in inspection.facts:
            ensure_area(f.area).inspection_facts.append(f)

    if thermal is not None:
        for f in thermal.facts:
            ensure_area(f.area).thermal_facts.append(f)

    merged_entries: list[MergedAreaEntry] = []

    for area_key in sorted(area_map.keys()):
        entry = area_map[area_key]

        entry.inspection_facts = _dedupe_facts(
            entry.inspection_facts,
            statement_fn=_inspection_statement,
            cfg=cfg,
        )
        entry.thermal_facts = _dedupe_facts(
            entry.thermal_facts,
            statement_fn=_thermal_statement,
            cfg=cfg,
        )

        # Conflict detection: do not resolve; store both statements and mark.
        conflicts: list[MergeConflict] = []
        for inf in entry.inspection_facts:
            if not _inspection_indicates_no_moisture(inf):
                continue
            for thf in entry.thermal_facts:
                if not _thermal_indicates_moisture_anomaly(thf):
                    continue
                conflicts.append(
                    MergeConflict(
                        type="inspection_no_moisture_vs_thermal_moisture_anomaly",
                        inspection_statement=_inspection_statement(inf),
                        thermal_statement=_thermal_statement(thf),
                        inspection_evidence=inf.evidence,
                        thermal_evidence=thf.evidence,
                        conflict_detected=True,
                    )
                )

        entry.conflicts = conflicts
        entry.conflict_detected = len(conflicts) > 0
        merged_entries.append(entry)

    return MergedAreaDataDoc(merged_areas=merged_entries)


def load_facts_docs(
    *,
    inspection_facts_path: str | Path,
    thermal_facts_path: str | Path,
) -> tuple[InspectionFactsDoc | None, ThermalFactsDoc | None]:
    insp_path = Path(inspection_facts_path)
    therm_path = Path(thermal_facts_path)

    inspection_doc: InspectionFactsDoc | None = None
    thermal_doc: ThermalFactsDoc | None = None

    if insp_path.exists():
        inspection_doc = InspectionFactsDoc.model_validate(json.loads(insp_path.read_text(encoding="utf-8")))

    if therm_path.exists():
        thermal_doc = ThermalFactsDoc.model_validate(json.loads(therm_path.read_text(encoding="utf-8")))

    return inspection_doc, thermal_doc


def run_merge_layer(
    *,
    inspection_facts_path: str,
    thermal_facts_path: str,
    out_dir: str,
    similarity_threshold: float = 0.92,
) -> Path:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    inspection_doc, thermal_doc = load_facts_docs(
        inspection_facts_path=inspection_facts_path,
        thermal_facts_path=thermal_facts_path,
    )

    merged = merge_and_dedupe(
        inspection=inspection_doc,
        thermal=thermal_doc,
        similarity_threshold=similarity_threshold,
    )

    out_file = out_path / "merged_area_data.json"
    out_file.write_text(merged.model_dump_json(indent=2), encoding="utf-8")
    return out_file
