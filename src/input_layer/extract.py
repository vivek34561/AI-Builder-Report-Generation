from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from .config import InputLayerConfig
from .ocr import ocr_image_file
from .pdf_render import render_pdf_page_to_png
from .pdf_text import extract_selectable_text_by_page, get_num_pages
from .types import DocumentExtraction, PageExtraction


def _process_single_page(
    pdf_path: str,
    page_idx: int,
    images_dir: str,
    dpi: int,
    ocr_confidence_threshold: float,
    selectable_text: str,
    source: str,
) -> tuple[int, PageExtraction]:
    """Process a single page in a separate process.
    
    This function is defined at module level to be picklable for ProcessPoolExecutor.
    Each process has its own memory space, avoiding pypdfium2 thread-safety issues.
    """
    page_number = page_idx + 1
    image_path = str(Path(images_dir) / f"page_{page_number:03}.png")
    
    render_pdf_page_to_png(
        pdf_path=pdf_path,
        page_index_zero_based=page_idx,
        dpi=dpi,
        out_path=image_path,
    )

    ocr = ocr_image_file(
        image_path=image_path,
        confidence_threshold=ocr_confidence_threshold,
    )

    page = PageExtraction(
        source=source,  # type: ignore[arg-type]
        pdf_path=str(Path(pdf_path)),
        page_number=page_number,
        raw_text=selectable_text,
        ocr_text=ocr.text,
        ocr_spans=ocr.spans,
        page_image_path=image_path,
        fields={},
    )
    return (page_idx, page)


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

    # Use ProcessPoolExecutor for true parallel processing
    # Each process has its own memory space, avoiding pypdfium2 thread-safety issues
    max_workers = min(4, num_pages)
    pages_dict: dict[int, PageExtraction] = {}
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all page processing tasks
        futures = {}
        for i in range(num_pages):
            future = executor.submit(
                _process_single_page,
                pdf_path,
                i,
                str(images_dir),
                config.dpi,
                config.ocr_confidence_threshold,
                selectable_text[i] if i < len(selectable_text) else "",
                source,
            )
            futures[future] = i
        
        # Collect results as they complete
        for future in as_completed(futures):
            page_idx, page = future.result()
            pages_dict[page_idx] = page
    
    # Sort pages by index to maintain correct order
    pages = [pages_dict[i] for i in range(num_pages)]

    return DocumentExtraction(source=source, pdf_path=str(Path(pdf_path)), pages=pages)  # type: ignore[arg-type]
