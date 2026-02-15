from __future__ import annotations

import json
import os
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.input_layer.config import InputLayerConfig
from src.input_layer.langgraph_input_layer import run_input_layer
from src.step2.langgraph_step2 import run_step2
from src.step2.merge_layer import run_merge_layer
from src.step3.reasoning_engine import run_analytical_reasoning
from src.step4.formatters import save_report
from src.step4.report_generator import generate_ddr_report


def _save_upload(upload: st.runtime.uploaded_file_manager.UploadedFile, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(upload.getvalue())
    return out_path


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


st.set_page_config(page_title="AI Builder DDR Report Generator", layout="wide")

st.title("🏗️ AI Builder - DDR Report Generation System")
st.caption(
    "Complete pipeline: PDF extraction → Fact extraction → Merge & conflict detection → "
    "Analytical reasoning → DDR report generation"
)

# Default paths
DEFAULT_STEP1_RUN = "20260214_184136"
DEFAULT_STEP1_OUTPUT_JSON = (
    Path("outputs")
    / "streamlit_runs"
    / DEFAULT_STEP1_RUN
    / "outputs"
    / "input_layer_output.json"
)

# Create tabs for all steps - Complete Pipeline first
tab_complete, tab_step1, tab_step2, tab_merge, tab_step3, tab_step4 = st.tabs([
    "🚀 Complete Pipeline",
    "📄 Step 1: Extract",
    "🔍 Step 2: Facts",
    "🔀 Merge & Conflicts",
    "🧠 Step 3: Reasoning",
    "📋 Step 4: DDR Report"
])


# ============================================================================
# STEP 1: PDF EXTRACTION
# ============================================================================
with tab_step1:
    st.header("Step 1: PDF Extraction (Input Layer)")
    st.write("Upload PDFs and extract structured data with page-level text and OCR.")

    col_left, col_right = st.columns(2)
    with col_left:
        inspection_pdf = st.file_uploader("Inspection Report (PDF)", type=["pdf"], key="inspection")
    with col_right:
        thermal_pdf = st.file_uploader("Thermal Report (PDF)", type=["pdf"], key="thermal")

    max_pages = st.number_input(
        "Max pages to process (0 = all)",
        min_value=0,
        value=0,
        step=1,
        help="Use this to keep checks fast on large PDFs.",
    )

    run_clicked = st.button(
        "🚀 Run extraction",
        type="primary",
        disabled=(inspection_pdf is None or thermal_pdf is None),
    )

    if run_clicked:
        run_root = Path("outputs") / "streamlit_runs" / time.strftime("%Y%m%d_%H%M%S")
        input_dir = run_root / "inputs"
        out_dir = run_root / "outputs"

        inspection_path = _save_upload(inspection_pdf, input_dir / "inspection.pdf")
        thermal_path = _save_upload(thermal_pdf, input_dir / "thermal.pdf")

        cfg = InputLayerConfig(max_pages=(None if int(max_pages) == 0 else int(max_pages)))

        with st.spinner("Extracting pages, running OCR, and writing JSON…"):
            output_json_path = run_input_layer(
                inspection_pdf=str(inspection_path),
                thermal_pdf=str(thermal_path),
                out_dir=str(out_dir),
                config=cfg,
            )

        out_path = Path(output_json_path)
        data = _load_json(out_path)

        st.success("✅ Extraction complete")
        st.code(str(out_path))

        # Store in session state for next steps
        st.session_state["step1_output"] = str(out_path)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "Download JSON",
                data=out_path.read_bytes(),
                file_name="input_layer_output.json",
                mime="application/json",
            )
        with col2:
            inspection_txt = out_path.parent / "inspection.txt"
            if inspection_txt.exists():
                st.download_button(
                    "Download inspection.txt",
                    data=inspection_txt.read_bytes(),
                    file_name="inspection.txt",
                    mime="text/plain",
                )
        with col3:
            thermal_txt = out_path.parent / "thermal.txt"
            if thermal_txt.exists():
                st.download_button(
                    "Download thermal.txt",
                    data=thermal_txt.read_bytes(),
                    file_name="thermal.txt",
                    mime="text/plain",
                )

        inspection_pages = (data.get("inspection") or {}).get("pages") or []
        thermal_pages = (data.get("thermal") or {}).get("pages") or []

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("Inspection pages", len(inspection_pages))
        with col_b:
            st.metric("Thermal pages", len(thermal_pages))
        with col_c:
            st.metric(
                "Inspection raw_text empty",
                sum(1 for p in inspection_pages if not (p.get("raw_text") or "").strip()),
            )
        with col_d:
            st.metric(
                "Thermal ocr_text empty",
                sum(1 for p in thermal_pages if not (p.get("ocr_text") or "").strip()),
            )


# ============================================================================
# STEP 2: FACT EXTRACTION
# ============================================================================
with tab_step2:
    st.header("Step 2: Structured Fact Extraction")
    st.write("Extract structured facts from the input layer output using LLM.")

    step1_json = st.text_input(
        "Step 1 output JSON",
        value=str(DEFAULT_STEP1_OUTPUT_JSON) if DEFAULT_STEP1_OUTPUT_JSON.exists() else "",
        help="Path to input_layer_output.json from Step 1"
    )

    out_dir_step2 = st.text_input("Step 2 output folder", value="outputs/step2_streamlit")
    preprocess_only = st.checkbox("Preprocess only (skip LLM extraction)", value=False)

    run_step2_clicked = st.button("🚀 Run Step 2", type="primary", key="run_step2")
    if run_step2_clicked:
        step1_path = Path(step1_json)
        if not step1_path.exists():
            st.error(f"Step 1 output not found: {step1_path}")
        else:
            with st.spinner("Running Step 2 (preprocess + extraction)…"):
                try:
                    run_step2(
                        input_json_path=str(step1_path),
                        out_dir=str(Path(out_dir_step2)),
                        run_llm=(not preprocess_only),
                    )
                    st.success("✅ Step 2 complete")

                    # Store in session state
                    st.session_state["step2_output"] = str(Path(out_dir_step2))

                except Exception as e:
                    st.error(f"Step 2 failed: {e}")

            out_path = Path(out_dir_step2)
            st.write("**Outputs:**")
            for filename in [
                "inspection_chunks.json",
                "thermal_chunks.json",
                "inspection_facts.json",
                "thermal_facts.json",
            ]:
                f = out_path / filename
                if f.exists():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.code(str(f))
                    with col2:
                        st.download_button(
                            f"Download",
                            data=f.read_bytes(),
                            file_name=filename,
                            key=f"dl_{filename}",
                        )


# ============================================================================
# MERGE & CONFLICT DETECTION
# ============================================================================
with tab_merge:
    st.header("Merge & Conflict Detection")
    st.write("Combine inspection and thermal facts by area, detect conflicts.")

    inspection_facts = st.text_input(
        "Inspection facts JSON",
        value="outputs/step2_streamlit/inspection_facts.json",
        key="merge_inspection"
    )
    thermal_facts = st.text_input(
        "Thermal facts JSON",
        value="outputs/step2_streamlit/thermal_facts.json",
        key="merge_thermal"
    )
    out_dir_merge = st.text_input("Merge output folder", value="outputs/merged_streamlit")

    run_merge_clicked = st.button("🚀 Run Merge", type="primary", key="run_merge")
    if run_merge_clicked:
        insp_path = Path(inspection_facts)
        therm_path = Path(thermal_facts)

        if not insp_path.exists() and not therm_path.exists():
            st.error("Neither facts file exists. Run Step 2 first.")
        else:
            with st.spinner("Merging and detecting conflicts…"):
                try:
                    out_file = run_merge_layer(
                        inspection_facts_path=str(insp_path),
                        thermal_facts_path=str(therm_path),
                        out_dir=str(Path(out_dir_merge)),
                    )
                    st.success("✅ Merge complete")
                    st.code(str(out_file))

                    # Store in session state
                    st.session_state["merged_output"] = str(out_file)

                    # Show preview
                    merged_data = _load_json(out_file)
                    st.write(f"**Total areas:** {len(merged_data.get('merged_areas', []))}")

                    conflicts = sum(
                        1 for area in merged_data.get('merged_areas', [])
                        if area.get('conflict_detected', False)
                    )
                    if conflicts > 0:
                        st.warning(f"⚠️ {conflicts} area(s) have conflicts")

                    st.download_button(
                        "Download merged_area_data.json",
                        data=out_file.read_bytes(),
                        file_name="merged_area_data.json",
                        mime="application/json",
                    )

                except Exception as e:
                    st.error(f"Merge failed: {e}")


# ============================================================================
# STEP 3: ANALYTICAL REASONING
# ============================================================================
with tab_step3:
    st.header("Step 3: Analytical Reasoning (Controlled LLM)")
    st.write("Infer root causes, assign severity, identify missing information - without hallucination.")

    merged_data_path = st.text_input(
        "Merged area data JSON",
        value="outputs/merged_streamlit/merged_area_data.json",
        key="reasoning_input"
    )
    out_dir_step3 = st.text_input("Step 3 output folder", value="outputs/step3_streamlit")

    # Check API key
    has_api_key = bool(os.getenv("GROQ_API_KEY"))
    if not has_api_key:
        st.warning("⚠️ GROQ_API_KEY not set. Set it in your environment to run Step 3.")

    run_step3_clicked = st.button(
        "🚀 Run Analytical Reasoning",
        type="primary",
        key="run_step3",
        disabled=not has_api_key
    )

    if run_step3_clicked:
        merged_path = Path(merged_data_path)
        if not merged_path.exists():
            st.error(f"Merged data not found: {merged_path}")
        else:
            with st.spinner("Running analytical reasoning (this may take a minute)…"):
                try:
                    out_file = run_analytical_reasoning(
                        merged_data_path=str(merged_path),
                        out_dir=str(Path(out_dir_step3)),
                    )
                    st.success("✅ Analytical reasoning complete")
                    st.code(str(out_file))

                    # Store in session state
                    st.session_state["step3_output"] = str(out_file)

                    # Show summary
                    analysis_data = _load_json(out_file)
                    areas = analysis_data.get('areas', [])

                    st.write(f"**Areas analyzed:** {len(areas)}")

                    # Count severity levels
                    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
                    for area in areas:
                        sev = area.get('severity', {}).get('severity_level', '').lower()
                        if sev in severity_counts:
                            severity_counts[sev] += 1

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Critical", severity_counts["critical"])
                    with col2:
                        st.metric("High", severity_counts["high"])
                    with col3:
                        st.metric("Medium", severity_counts["medium"])
                    with col4:
                        st.metric("Low", severity_counts["low"])

                    st.download_button(
                        "Download analytical_reasoning.json",
                        data=out_file.read_bytes(),
                        file_name="analytical_reasoning.json",
                        mime="application/json",
                    )

                except Exception as e:
                    st.error(f"Analytical reasoning failed: {e}")


# ============================================================================
# STEP 4: DDR REPORT GENERATION
# ============================================================================
with tab_step4:
    st.header("Step 4: DDR Report Generation")
    st.write("Generate professional client-ready reports in multiple formats.")

    analysis_path = st.text_input(
        "Analytical reasoning JSON",
        value="outputs/step3_streamlit/analytical_reasoning.json",
        key="ddr_input"
    )
    property_name = st.text_input("Property name", value="Property Inspection Report")
    out_dir_step4 = st.text_input("Step 4 output folder", value="outputs/ddr_streamlit")

    format_options = st.multiselect(
        "Output formats",
        ["markdown", "txt", "pdf"],
        default=["markdown", "txt"]
    )

    run_step4_clicked = st.button("🚀 Generate DDR Report", type="primary", key="run_step4")

    if run_step4_clicked:
        analysis_file = Path(analysis_path)
        if not analysis_file.exists():
            st.error(f"Analysis file not found: {analysis_file}")
        else:
            with st.spinner("Generating DDR report…"):
                try:
                    # Generate report
                    ddr_report = generate_ddr_report(
                        analysis_path=str(analysis_file),
                        property_name=property_name,
                    )

                    # Save in requested formats
                    output_dir = Path(out_dir_step4)
                    saved_files = save_report(ddr_report, output_dir, format_options)

                    st.success("✅ DDR Report generated successfully!")

                    # Show summary
                    summary = ddr_report.property_issue_summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Areas", summary.total_areas_inspected)
                    with col2:
                        st.metric("Areas with Issues", summary.areas_with_issues)
                    with col3:
                        st.metric("Overall Risk", summary.overall_risk_level)

                    st.write("**Severity Breakdown:**")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Critical", summary.critical_count)
                    with col2:
                        st.metric("High", summary.high_count)
                    with col3:
                        st.metric("Medium", summary.medium_count)
                    with col4:
                        st.metric("Low", summary.low_count)

                    st.divider()

                    # Download buttons
                    st.write("**Download Reports:**")
                    for format_name, file_path in saved_files.items():
                        if file_path.exists():
                            st.download_button(
                                f"📥 Download {format_name.upper()} Report",
                                data=file_path.read_bytes(),
                                file_name=file_path.name,
                                key=f"dl_ddr_{format_name}",
                            )

                    # Preview markdown
                    if "markdown" in saved_files:
                        md_path = saved_files["markdown"]
                        if md_path.exists():
                            with st.expander("📄 Preview Markdown Report", expanded=True):
                                st.markdown(md_path.read_text(encoding="utf-8"))

                except Exception as e:
                    st.error(f"DDR generation failed: {e}")


# ============================================================================
# COMPLETE PIPELINE
# ============================================================================
with tab_complete:
    st.header("🚀 Complete Pipeline (All Steps)")
    st.write("Run the entire pipeline from PDF upload to DDR report generation.")

    st.info(
        "This tab will run all steps sequentially. Make sure you have:\n"
        "- Uploaded PDFs in Step 1\n"
        "- Set GROQ_API_KEY environment variable\n"
        "- Sufficient API credits"
    )

    col_left, col_right = st.columns(2)
    with col_left:
        inspection_pdf_full = st.file_uploader(
            "Inspection Report (PDF)",
            type=["pdf"],
            key="inspection_full"
        )
    with col_right:
        thermal_pdf_full = st.file_uploader(
            "Thermal Report (PDF)",
            type=["pdf"],
            key="thermal_full"
        )

    property_name_full = st.text_input(
        "Property name for report",
        value="Property Inspection Report",
        key="property_full"
    )

    run_complete_clicked = st.button(
        "🚀 Run Complete Pipeline",
        type="primary",
        disabled=(inspection_pdf_full is None or thermal_pdf_full is None),
        key="run_complete"
    )

    if run_complete_clicked:
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # Step 1: Extract
            status_text.text("Step 1/5: Extracting PDFs...")
            progress_bar.progress(10)

            run_root = Path("outputs") / "streamlit_runs" / time.strftime("%Y%m%d_%H%M%S")
            input_dir = run_root / "inputs"
            out_dir = run_root / "outputs"

            inspection_path = _save_upload(inspection_pdf_full, input_dir / "inspection.pdf")
            thermal_path = _save_upload(thermal_pdf_full, input_dir / "thermal.pdf")

            cfg = InputLayerConfig(max_pages=None)
            output_json_path = run_input_layer(
                inspection_pdf=str(inspection_path),
                thermal_pdf=str(thermal_path),
                out_dir=str(out_dir),
                config=cfg,
            )
            progress_bar.progress(20)

            # Step 2: Extract facts
            status_text.text("Step 2/5: Extracting structured facts...")
            step2_out = run_root / "step2"
            run_step2(
                input_json_path=str(output_json_path),
                out_dir=str(step2_out),
                run_llm=True,
            )
            progress_bar.progress(40)

            # Merge
            status_text.text("Step 3/5: Merging and detecting conflicts...")
            merge_out = run_root / "merged"
            merged_file = run_merge_layer(
                inspection_facts_path=str(step2_out / "inspection_facts.json"),
                thermal_facts_path=str(step2_out / "thermal_facts.json"),
                out_dir=str(merge_out),
            )
            progress_bar.progress(60)

            # Step 3: Analytical reasoning
            status_text.text("Step 4/5: Running analytical reasoning...")
            step3_out = run_root / "step3"
            analysis_file = run_analytical_reasoning(
                merged_data_path=str(merged_file),
                out_dir=str(step3_out),
            )
            progress_bar.progress(80)

            # Step 4: Generate DDR
            status_text.text("Step 5/5: Generating DDR report...")
            step4_out = run_root / "ddr"
            ddr_report = generate_ddr_report(
                analysis_path=str(analysis_file),
                property_name=property_name_full,
            )
            saved_files = save_report(ddr_report, step4_out, ["markdown", "txt"])
            progress_bar.progress(100)

            status_text.text("✅ Complete pipeline finished!")

            st.success("🎉 All steps completed successfully!")

            # Show summary
            summary = ddr_report.property_issue_summary
            st.write("### Report Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Areas", summary.total_areas_inspected)
            with col2:
                st.metric("Areas with Issues", summary.areas_with_issues)
            with col3:
                st.metric("Overall Risk", summary.overall_risk_level)

            # Download reports
            st.write("### Download Reports")
            for format_name, file_path in saved_files.items():
                if file_path.exists():
                    st.download_button(
                        f"📥 Download {format_name.upper()} Report",
                        data=file_path.read_bytes(),
                        file_name=file_path.name,
                        key=f"dl_complete_{format_name}",
                    )

            # Preview
            if "markdown" in saved_files:
                md_path = saved_files["markdown"]
                if md_path.exists():
                    with st.expander("📄 Preview DDR Report", expanded=True):
                        st.markdown(md_path.read_text(encoding="utf-8"))

        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            import traceback
            st.code(traceback.format_exc())


# Sidebar with info
with st.sidebar:
    st.header("ℹ️ About")
    st.write(
        "This system implements a complete AI-powered DDR (Detailed Diagnostic Report) "
        "generation pipeline for building inspections."
    )

    st.write("**Pipeline Steps:**")
    st.write("1. 📄 PDF Extraction")
    st.write("2. 🔍 Fact Extraction")
    st.write("3. 🔀 Merge & Conflicts")
    st.write("4. 🧠 Analytical Reasoning")
    st.write("5. 📋 DDR Report Generation")

    st.divider()

    st.write("**Key Features:**")
    st.write("✅ Evidence-based reasoning")
    st.write("✅ No hallucination")
    st.write("✅ Conflict detection")
    st.write("✅ Multi-format output")

    st.divider()

    # Show session state
    if st.checkbox("Show session state"):
        st.json(dict(st.session_state))
