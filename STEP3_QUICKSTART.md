# Step 3: Analytical Reasoning Layer - Quick Start Guide

## Overview

Step 3 adds **controlled LLM reasoning** to process merged area data and generate evidence-based analysis with:
- Root cause inference (with confidence levels)
- Severity assessment (critical/high/medium/low)
- Missing information identification
- **No hallucination** - only references provided facts

## Installation

No additional dependencies needed beyond existing requirements.

## Usage

### 1. Set API Key

```bash
setx GROQ_API_KEY "<your_groq_api_key>"
```

### 2. Run Analysis

```bash
python run_step3_reasoning.py \
  --merged-data outputs/merged/merged_area_data.json \
  --out outputs/step3
```

### 3. View Results

Output: `outputs/step3/analytical_reasoning.json`

## Example Output

For each area, you get:

```json
{
  "area": "Bedroom wall",
  "root_cause": {
    "probable_cause": "Active water intrusion through exterior wall",
    "reasoning": "Both inspection and thermal data confirm moisture...",
    "supporting_evidence": [
      "Page 3: 'Bedroom wall shows visible moisture staining...'",
      "Page 2: 'Thermal imaging shows coldspot at 15.2°C...'"
    ],
    "confidence": "high",
    "evidence_gaps": ["No exterior wall inspection performed"]
  },
  "severity": {
    "severity_level": "critical",
    "reasoning": "Active moisture intrusion with confirmed surface damage...",
    "risk_factors": [
      "Active moisture intrusion confirmed by multiple methods",
      "Moisture content at 18% (significantly above safe levels)"
    ]
  },
  "missing_information": [
    {
      "category": "exterior_inspection",
      "description": "No exterior wall inspection to identify entry point",
      "impact": "Cannot determine source of water intrusion"
    }
  ]
}
```

## Key Features

✅ **Evidence Citations**: Every inference cites page numbers and quotes  
✅ **Confidence Levels**: high/medium/low/insufficient_evidence  
✅ **Conflict Handling**: Explains both perspectives when data conflicts  
✅ **No Hallucination**: Returns "Not Available" when evidence is insufficient  

## Files Created

- `src/step3/models.py` - Data models with evidence requirements
- `src/step3/reasoning_engine.py` - Controlled LLM reasoning logic
- `run_step3_reasoning.py` - Command-line runner

## Next Steps

Use the analytical reasoning output to generate the final DDR report with:
- Property issue summary
- Area-wise observations
- Root causes (from Step 3)
- Severity assessments (from Step 3)
- Recommended actions
- Missing information (from Step 3)
