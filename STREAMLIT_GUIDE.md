# Streamlit Frontend - Complete Pipeline UI

The Streamlit app (`streamlit_app.py`) now includes all pipeline steps with an interactive UI.

## Features

### 6 Tabs for Complete Workflow

1. **📄 Step 1: Extract** - Upload PDFs, extract text and OCR
2. **🔍 Step 2: Facts** - Extract structured facts using LLM
3. **🔀 Merge & Conflicts** - Combine data by area, detect conflicts
4. **🧠 Step 3: Reasoning** - Analytical reasoning with controlled LLM
5. **📋 Step 4: DDR Report** - Generate client-ready reports (MD/PDF/TXT)
6. **🚀 Complete Pipeline** - Run all steps end-to-end

### Key Features

- **Progress Tracking**: Visual progress bars for long-running operations
- **Download Buttons**: Download outputs at each step
- **Live Preview**: Preview markdown reports directly in the browser
- **Session State**: Maintains paths between steps for easy workflow
- **Error Handling**: Clear error messages and validation
- **Metrics Dashboard**: Real-time stats for each step

## Running the App

```bash
streamlit run streamlit_app.py
```

Then open your browser to the provided URL (usually http://localhost:8501)

## Usage

### Quick Start (Individual Steps)

1. Go to **Step 1** tab, upload PDFs, click "Run extraction"
2. Go to **Step 2** tab, verify paths, click "Run Step 2"
3. Go to **Merge** tab, click "Run Merge"
4. Go to **Step 3** tab, click "Run Analytical Reasoning"
5. Go to **Step 4** tab, select formats, click "Generate DDR Report"

### Complete Pipeline

1. Go to **Complete Pipeline** tab
2. Upload both PDFs
3. Enter property name
4. Click "Run Complete Pipeline"
5. Wait for all steps to complete
6. Download generated reports

## Requirements

- GROQ_API_KEY environment variable must be set for Steps 3 & 4
- All dependencies from requirements.txt installed

## Output

All outputs are saved to `outputs/streamlit_runs/<timestamp>/` with subdirectories for each step.
