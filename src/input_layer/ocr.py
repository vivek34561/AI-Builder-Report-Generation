from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception as e:  # pragma: no cover
    RapidOCR = None  # type: ignore

from .types import OCRSpan


@dataclass(frozen=True)
class OCRResult:
    text: str
    spans: list[OCRSpan]


def ocr_image_file(image_path: str, confidence_threshold: float) -> OCRResult:
    """OCR a rendered page image.

    Uses RapidOCR (ONNXRuntime) to avoid requiring an external Tesseract install.
    """
    if RapidOCR is None:
        raise RuntimeError(
            "rapidocr-onnxruntime is not available. Install requirements.txt dependencies."
        )

    engine = RapidOCR()

    img = cv2.imread(str(Path(image_path)))
    if img is None:
        return OCRResult(text="", spans=[])

    # returns: (result, elapsed)
    result, _elapsed = engine(img)

    spans: list[OCRSpan] = []
    lines: list[str] = []

    if result:
        for item in result:
            # item: [ [x1,y1]...[x4,y4], text, score ]
            if len(item) >= 3:
                text = (item[1] or "").strip()
                score = float(item[2]) if item[2] is not None else None
                if not text:
                    continue
                if score is not None and score < confidence_threshold:
                    continue
                spans.append(OCRSpan(text=text, confidence=score))
                lines.append(text)

    full_text = "\n".join(lines).strip()
    return OCRResult(text=full_text, spans=spans)
