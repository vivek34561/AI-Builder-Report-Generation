# Step 4: DDR Report Generation - Quick Start

## Overview

Step 4 generates professional, client-ready **Detailed Diagnostic Reports (DDR)** from analytical reasoning data in multiple formats.

## Usage

```bash
python run_step4_generate_ddr.py \
  --analysis outputs/step3/analytical_reasoning.json \
  --out outputs/ddr \
  --format markdown pdf txt
```

## Output Formats

- **Markdown** (.md) - Rich formatting, easy to edit
- **PDF** (.pdf) - Professional client deliverable
- **Plain Text** (.txt) - Maximum compatibility

## DDR Report Sections

The generated report contains exactly these 7 sections:

1. **Property Issue Summary** - Overview, severity counts, key findings
2. **Area-wise Observations** - Detailed findings per area
3. **Probable Root Cause** - Evidence-based inferences
4. **Severity Assessment** - Ratings with reasoning
5. **Recommended Actions** - Prioritized by urgency
6. **Additional Notes** - Cross-cutting observations
7. **Missing Information** - Explicitly listed gaps

## Example Output

See: `outputs/test_sample/ddr/DDR_Report.md`

## Key Features

✅ No new facts (only uses analytical reasoning data)  
✅ Client-friendly language  
✅ Conflicts clearly marked  
✅ Evidence citations preserved  
✅ Actions prioritized by severity  

## Files Created

- `src/step4/models.py` - DDR data models
- `src/step4/report_generator.py` - Report generation logic
- `src/step4/formatters.py` - Multi-format output
- `run_step4_generate_ddr.py` - Command-line runner
