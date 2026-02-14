from __future__ import annotations

import warnings

from pypdf import PdfReader


warnings.filterwarnings(
    "ignore",
    message=r"Multiple definitions in dictionary.*",
)


def extract_selectable_text_by_page(pdf_path: str) -> list[str]:
    """Return a list of per-page selectable text (may be empty strings)."""
    reader = PdfReader(pdf_path, strict=False)
    texts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        texts.append(_clean_text(text))
    return texts


def get_num_pages(pdf_path: str) -> int:
    reader = PdfReader(pdf_path, strict=False)
    return len(reader.pages)


def _clean_text(text: str) -> str:
    # Keep cleaning conservative; we want auditable extraction.
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()
