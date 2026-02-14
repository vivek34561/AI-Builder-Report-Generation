from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InputLayerConfig:
    dpi: int = 220
    ocr_confidence_threshold: float = 0.55
    max_pages: int | None = None

    # Where to write rendered page images
    images_subdir: str = "page_images"
