# AI-Builder-Report-Generation

## Step 1 (Input Layer) — LangGraph PDF Extraction

Goal: turn mixed-format PDFs (selectable text + image-heavy pages) into **auditable, page-level JSON**.

This layer does **no reasoning** and **does not invent facts**. It only:
- extracts selectable text per page
- renders each page to an image
- runs OCR on the rendered image to capture image-embedded labels/captions (especially for thermal reports)

### Install

Create/activate a Python venv, then:

`pip install -r requirements.txt`

### Run

`python run_input_layer.py --inspection <Inspection.pdf> --thermal <Thermal.pdf> --out outputs`

### Streamlit checker (recommended for quick validation)

`streamlit run streamlit_app.py`

Upload the two PDFs and click **Run extraction**. The app will:
- render pages to images
- extract selectable text
- OCR image-embedded labels/captions
- let you preview per-page `raw_text` and `ocr_text`

Outputs:
- `outputs/input_layer_output.json` (structured per-page extraction)
- `outputs/inspection.txt` (page-by-page concatenation of extracted text)
- `outputs/thermal.txt` (page-by-page concatenation of extracted text)
- `outputs/page_images/<pdf_stem>/page_XXX.png` (rendered pages used for OCR)

### Notes

- If OCR can’t confidently read something, it simply won’t appear in `ocr_text`; downstream steps should mark such values as **Not Available**.
- This is designed to generalize to similar inspection/thermal PDF formats.

## Step 2 — Pre-processing + Structured Fact Extraction

Step 2 produces:
- deterministic cleaned chunks (no AI)
- schema-based facts extracted by an LLM (one call per document)

### Run

Set your Groq key:

`setx GROQ_API_KEY "<your_key>"`

Then run:

`python run_step2_extract_facts.py --input-json <path-to-input_layer_output.json> --out outputs/step2`

For build/demo convenience, `run_step2_extract_facts.py` currently defaults `--input-json` to:

`outputs/streamlit_runs/20260214_184136/outputs/input_layer_output.json`

Outputs:
- `outputs/step2/inspection_chunks.json`
- `outputs/step2/thermal_chunks.json`
- `outputs/step2/inspection_facts.json`
- `outputs/step2/thermal_facts.json`

## Merge + De-dup + Conflict Detection (Area-Level)

Purpose: combine inspection + thermal facts **by area**, remove duplicate observations, and flag conflicts (without resolving them).

Rules:
- Group facts by `area` (e.g., Bedroom wall, Bathroom ceiling)
- Merge inspection and thermal entries for the same area
- De-duplicate observations using string similarity
- Detect conflicts (example): inspection indicates **no moisture**, thermal indicates **moisture anomaly**
- Conflict handling: do **not** auto-resolve; store both statements and mark `conflict_detected = true`

### Run

`python run_merge_area_data.py --inspection-facts outputs/step2/inspection_facts.json --thermal-facts outputs/step2/thermal_facts.json --out outputs/merged`

Output:
- `outputs/merged/merged_area_data.json`