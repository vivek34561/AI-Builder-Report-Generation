from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium


def render_pdf_page_to_png(
    pdf_path: str,
    page_index_zero_based: int,
    dpi: int,
    out_path: str,
) -> str:
    """Render a single PDF page to a PNG image at the given path.

    Returns the written path.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    pdf = pdfium.PdfDocument(pdf_path)
    page = pdf.get_page(page_index_zero_based)
    scale = dpi / 72  # PDF points are 72 DPI
    bitmap = page.render(scale=scale)
    pil_image = bitmap.to_pil()
    pil_image.save(out, format="PNG")

    # Explicit cleanup
    page.close()
    pdf.close()

    return str(out)
