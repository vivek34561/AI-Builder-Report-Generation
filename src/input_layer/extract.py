from __future__ import annotations

from pathlib import Path

from .config import InputLayerConfig
from .ocr import ocr_image_file
from .pdf_render import render_pdf_page_to_png
from .pdf_text import extract_selectable_text_by_page, get_num_pages
from .types import DocumentExtraction, PageExtraction


def extract_document(
    *,
    pdf_path: str,
    source: str,
    out_dir: str,
    config: InputLayerConfig,
) -> DocumentExtraction:
    out = Path(out_dir)
    images_dir = out / config.images_subdir / Path(pdf_path).stem
    images_dir.mkdir(parents=True, exist_ok=True)

    num_pages = get_num_pages(pdf_path)
    selectable_text = extract_selectable_text_by_page(pdf_path)

    if config.max_pages is not None:
        num_pages = min(num_pages, config.max_pages)
        selectable_text = selectable_text[:num_pages]

    pages: list[PageExtraction] = []

    for page_idx in range(num_pages):
        page_number = page_idx + 1
        image_path = str(images_dir / f"page_{page_number:03}.png")
        render_pdf_page_to_png(
            pdf_path=pdf_path,
            page_index_zero_based=page_idx,
            dpi=config.dpi,
            out_path=image_path,
        )

        ocr = ocr_image_file(
            image_path=image_path,
            confidence_threshold=config.ocr_confidence_threshold,
        )

        page = PageExtraction(
            source=source,  # type: ignore[arg-type]
            pdf_path=str(Path(pdf_path)),
            page_number=page_number,
            raw_text=selectable_text[page_idx] if page_idx < len(selectable_text) else "",
            ocr_text=ocr.text,
            ocr_spans=ocr.spans,
            page_image_path=image_path,
            fields={},
        )
        pages.append(page)

    return DocumentExtraction(source=source, pdf_path=str(Path(pdf_path)), pages=pages)  # type: ignore[arg-type]
