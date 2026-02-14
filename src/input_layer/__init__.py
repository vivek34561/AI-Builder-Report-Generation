"""Input layer: auditable extraction of mixed-format PDFs.

This layer performs:
- PDF page rendering to images
- selectable-text extraction
- OCR over rendered images (for image-embedded labels/captions)

No summarization or reasoning should happen here.
"""
