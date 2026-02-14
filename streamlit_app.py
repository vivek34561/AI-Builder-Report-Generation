from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st

from src.input_layer.config import InputLayerConfig
from src.input_layer.langgraph_input_layer import run_input_layer
from src.step2.langgraph_step2 import run_step2


def _save_upload(upload: st.runtime.uploaded_file_manager.UploadedFile, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(upload.getvalue())
    return out_path


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


st.set_page_config(page_title="DDR Input Layer Checker", layout="wide")

st.title("DDR Input Layer Checker (Step 1)")
st.caption(
    "Uploads two PDFs (Inspection + Thermal), runs page rendering + selectable text extraction + OCR, "
    "and lets you preview the auditable output."
)

DEFAULT_STEP1_RUN = "20260214_184136"
DEFAULT_STEP1_OUTPUT_JSON = (
    Path("outputs")
    / "streamlit_runs"
    / DEFAULT_STEP1_RUN
    / "outputs"
    / "input_layer_output.json"
)

tab_step1, tab_step2 = st.tabs(["Step 1 (Extract)", "Step 2 (From Cached Step 1)"])


with tab_step1:

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
        "Run extraction",
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

        st.success("Extraction complete")
        st.write("Output JSON:")
        st.code(str(out_path))

        st.download_button(
            "Download JSON",
            data=out_path.read_bytes(),
            file_name="input_layer_output.json",
            mime="application/json",
        )

        inspection_txt = out_path.parent / "inspection.txt"
        thermal_txt = out_path.parent / "thermal.txt"
        col_dl_1, col_dl_2 = st.columns(2)
        with col_dl_1:
            if inspection_txt.exists():
                st.download_button(
                    "Download inspection.txt",
                    data=inspection_txt.read_bytes(),
                    file_name="inspection.txt",
                    mime="text/plain",
                )
        with col_dl_2:
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

        st.divider()

        viewer_left, viewer_right = st.columns([1, 2])

        with viewer_left:
            doc_choice = st.selectbox("Document", ["inspection", "thermal"], index=0)
            pages = inspection_pages if doc_choice == "inspection" else thermal_pages

            if not pages:
                st.warning("No pages found for this document")
            else:
                page_numbers = [p.get("page_number") for p in pages]
                page_choice = st.selectbox("Page", page_numbers, index=0)

                selected = next((p for p in pages if p.get("page_number") == page_choice), pages[0])
                st.write("Fields (no inference):")
                st.json(selected.get("fields") or {})

        with viewer_right:
            if inspection_pages or thermal_pages:
                pages = inspection_pages if doc_choice == "inspection" else thermal_pages
                if pages:
                    selected = next((p for p in pages if p.get("page_number") == page_choice), pages[0])
                    img_path = selected.get("page_image_path")
                    if img_path and Path(img_path).exists():
                        st.image(str(img_path), caption=f"{doc_choice} page {selected.get('page_number')}")
                    else:
                        st.info("Page image not found (unexpected).")

                    st.subheader("Selectable text (raw_text)")
                    st.text_area(
                        "raw_text",
                        value=(selected.get("raw_text") or ""),
                        height=220,
                        label_visibility="collapsed",
                        key=f"{doc_choice}_raw_{selected.get('page_number')}",
                    )

                    st.subheader("OCR text (ocr_text)")
                    st.text_area(
                        "ocr_text",
                        value=(selected.get("ocr_text") or ""),
                        height=220,
                        label_visibility="collapsed",
                        key=f"{doc_choice}_ocr_{selected.get('page_number')}",
                    )

                    with st.expander("View full page JSON", expanded=False):
                        st.json(selected)


with tab_step2:
    st.subheader("Run Step 2 using cached Step 1 output")
    st.write(
        "This is useful for fast iteration: you skip PDF rendering + OCR and jump straight to Step 2. "
        "For final demo/submission, you should still show the full pipeline works end-to-end."
    )

    st.write("Cached Step 1 output JSON:")
    st.code(str(DEFAULT_STEP1_OUTPUT_JSON))

    out_dir = st.text_input("Step 2 output folder", value="outputs/step2_from_cached")
    preprocess_only = st.checkbox("Preprocess only (skip LLM extraction)", value=True)

    run_step2_clicked = st.button("Run Step 2", type="primary")
    if run_step2_clicked:
        if not DEFAULT_STEP1_OUTPUT_JSON.exists():
            st.error("Cached Step 1 output not found. Run Step 1 once or update DEFAULT_STEP1_RUN.")
        else:
            with st.spinner("Running Step 2 (preprocess + optional extraction)…"):
                try:
                    run_step2(
                        input_json_path=str(DEFAULT_STEP1_OUTPUT_JSON),
                        out_dir=str(Path(out_dir)),
                        run_llm=(not preprocess_only),
                    )
                    st.success("Step 2 complete")
                except Exception as e:
                    # Preprocess files may still exist even if extraction failed (e.g., GROQ_API_KEY missing)
                    st.warning(f"Step 2 finished with an error: {e}")

            out_path = Path(out_dir)
            st.write("Outputs:")
            for filename in [
                "inspection_chunks.json",
                "thermal_chunks.json",
                "inspection_facts.json",
                "thermal_facts.json",
            ]:
                f = out_path / filename
                if f.exists():
                    st.code(str(f))
                    st.download_button(
                        f"Download {filename}",
                        data=f.read_bytes(),
                        file_name=filename,
                    )
