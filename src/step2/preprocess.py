from __future__ import annotations

import re
from collections import Counter


_PAGE_NUMBER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*page\s*\d+\s*(of\s*\d+)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*/\s*\d+\s*$"),
]


def normalize_units(text: str) -> str:
    """Normalize unit formatting without converting values."""
    s = text

    # Temperature
    s = re.sub(r"(\d)\s*°\s*C\b", r"\1 °C", s)
    s = re.sub(r"(\d)\s*deg\s*C\b", r"\1 °C", s, flags=re.IGNORECASE)

    # Percent
    s = re.sub(r"(\d)\s*%", r"\1 %", s)

    # Millimeters
    s = re.sub(r"(\d)\s*mm\b", r"\1 mm", s, flags=re.IGNORECASE)

    return s


def clean_text(text: str) -> str:
    s = text.replace("\u00a0", " ")
    # Strip control characters (common in some PDF text extractions),
    # but keep newlines/tabs for structure.
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    s = "\n".join(line.rstrip() for line in s.splitlines())
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def remove_common_boilerplate(page_texts: list[str], *, min_fraction: float = 0.6) -> list[str]:
    """Remove lines that repeat across many pages (headers/footers/branding).

    Deterministic heuristic:
    - Count exact line strings across pages
    - Drop lines that appear in >= min_fraction of pages

    This is conservative: it removes only very common lines.
    """
    if not page_texts:
        return []

    pages_lines = [
        [ln.strip() for ln in t.splitlines() if ln.strip()]
        for t in page_texts
    ]

    counts: Counter[str] = Counter()
    for lines in pages_lines:
        counts.update(set(lines))

    threshold = max(2, int(len(page_texts) * min_fraction))
    common = {line for line, c in counts.items() if c >= threshold}

    cleaned_pages: list[str] = []
    for lines in pages_lines:
        kept = [ln for ln in lines if ln not in common]
        cleaned_pages.append("\n".join(kept).strip())

    return cleaned_pages


def remove_page_numbers(text: str) -> str:
    out_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out_lines.append("")
            continue
        if any(p.match(stripped) for p in _PAGE_NUMBER_PATTERNS):
            continue
        out_lines.append(line)
    return "\n".join(out_lines).strip()


def dedupe_lines_keep_order(text: str) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for line in text.splitlines():
        key = line.strip()
        if not key:
            out.append("")
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    return "\n".join(out).strip()


def combine_raw_and_ocr(raw_text: str, ocr_text: str) -> str:
    # Keep both, but dedupe repeated lines.
    merged = (raw_text or "").strip()
    if ocr_text and ocr_text.strip():
        if merged:
            merged = merged + "\n" + ocr_text.strip()
        else:
            merged = ocr_text.strip()
    merged = dedupe_lines_keep_order(merged)
    merged = remove_page_numbers(merged)
    merged = normalize_units(merged)
    merged = clean_text(merged)
    return merged
