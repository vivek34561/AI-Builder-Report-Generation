from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    source: str
    page_numbers: list[int]
    text: str


def chunk_pages(
    *,
    source: str,
    pages: list[tuple[int, str]],
    max_chars: int = 1400,
) -> list[TextChunk]:
    """Split cleaned page text into logical-ish chunks.

    Deterministic strategy:
    - split by blank lines into paragraphs
    - accumulate paragraphs until max_chars
    - keep page number provenance
    """
    chunks: list[TextChunk] = []

    cur_parts: list[str] = []
    cur_pages: set[int] = set()

    def flush() -> None:
        nonlocal cur_parts, cur_pages
        text = "\n\n".join([p for p in cur_parts if p.strip()]).strip()
        if text:
            chunks.append(TextChunk(source=source, page_numbers=sorted(cur_pages), text=text))
        cur_parts = []
        cur_pages = set()

    for page_no, text in pages:
        if not text.strip():
            continue
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for para in paragraphs:
            candidate = ("\n\n".join(cur_parts + [para])).strip()
            if cur_parts and len(candidate) > max_chars:
                flush()
            cur_parts.append(para)
            cur_pages.add(page_no)

            if len("\n\n".join(cur_parts)) >= max_chars:
                flush()

    flush()
    return chunks
