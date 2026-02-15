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

## Step 3 — Analytical Reasoning Layer (Controlled LLM)

Purpose: apply **controlled LLM reasoning** over structured data to infer root causes, assign severity, and identify missing information—**without hallucination**.

This layer:
- Only references facts from `merged_area_data.json`
- Returns "Not Available" when evidence is insufficient
- Cites specific evidence (page numbers, quotes) for all inferences
- Never invents or assumes information

### Run

Ensure your Groq API key is set:

`setx GROQ_API_KEY "<your_key>"`

Then run:

`python run_step3_reasoning.py --merged-data outputs/merged/merged_area_data.json --out outputs/step3`

### Output

- `outputs/step3/analytical_reasoning.json`

Contains for each area:
- **Root Cause Inference**: probable cause with reasoning, supporting evidence, and confidence level
- **Severity Assessment**: severity rating (critical/high/medium/low) with risk factors and reasoning
- **Missing Information**: explicitly identified gaps in the data
- **Summaries**: inspection and thermal findings summary

### Key Features

**Evidence-Based Reasoning**: Every inference must cite specific quotes or page numbers from source documents.

**Confidence Levels**: `high`, `medium`, `low`, or `insufficient_evidence` based on data quality.

**Conflict Handling**: When inspection and thermal data conflict, both perspectives are presented with evidence.

**No Hallucination**: The LLM is explicitly constrained to only use provided facts. If information is missing, it says "Not Available" rather than guessing.

## Step 4 — DDR Report Generation (Final Output)

Purpose: convert structured analysis into a professional, client-friendly **Detailed Diagnostic Report (DDR)** in multiple formats.

This layer:
- Uses only facts from `analytical_reasoning.json` (no new facts)
- Generates reports in Markdown, PDF, and plain text formats
- Uses simple, client-friendly language
- Explicitly mentions conflicts and missing information
- Follows the exact DDR structure required by the assignment

### Run

```bash
python run_step4_generate_ddr.py \
  --analysis outputs/step3/analytical_reasoning.json \
  --out outputs/ddr \
  --format markdown pdf txt
```

Options:
- `--format`: Choose output formats (`markdown`, `pdf`, `txt`, or `all`)
- `--property-name`: Custom property name for report header

### Output

Generated reports in `outputs/ddr/`:
- `DDR_Report.md` - Markdown format with rich formatting
- `DDR_Report.pdf` - Professional PDF for client delivery
- `DDR_Report.txt` - Plain text for maximum compatibility

### DDR Report Structure

The generated report contains exactly these sections (as required):

1. **Property Issue Summary** - High-level overview, severity counts, key findings
2. **Area-wise Observations** - Detailed findings for each area, conflicts highlighted
3. **Probable Root Cause** - Inferred causes with reasoning, evidence, and confidence levels
4. **Severity Assessment (with Reasoning)** - Severity ratings with risk factors
5. **Recommended Actions** - Prioritized by severity (Immediate/Short-term/Medium-term/Monitoring)
6. **Additional Notes** - Cross-cutting observations and general recommendations
7. **Missing or Unclear Information** - Explicitly listed gaps with impact assessment

### Key Features

**Client-Friendly Language**: Technical jargon avoided, simple explanations provided.

**Evidence Preservation**: All page references and quotes from source documents maintained.

**Conflict Transparency**: Conflicts between inspection and thermal data clearly marked with ⚠️.

**Prioritized Actions**: Recommendations organized by urgency based on severity levels.

**Multiple Formats**: Choose the format that best suits your needs (Markdown for editing, PDF for clients, TXT for compatibility).

