import streamlit as st
from app.llm.vectorize_os import run_pipeline as run_pipeline_os

st.set_page_config(page_title="AICCRA generator", page_icon="📄")

st.title("📄 AICCRA Report Generator")

indicators = [
    "IPI 1.1",
    "IPI 1.2",
    "IPI 1.3",
    "IPI 1.4",
    "IPI 2.1",
    "IPI 2.2",
    "IPI 2.3",
    "IPI 3.1",
    "IPI 3.2",
    "IPI 3.3",
    "IPI 3.4",
    "PDO Indicator 1",
    "PDO Indicator 2",
    "PDO Indicator 3",
    "PDO Indicator 4",
    "PDO Indicator 5"
]

selected_indicator = st.selectbox("Select an indicator:", indicators)
selected_year = st.selectbox("Select a year:", [2024, 2025])

if st.button("Generate report"):
    with st.spinner("Generating report..."):
        try:
            response = run_pipeline_os(selected_indicator, selected_year)
            st.markdown(response)

        except Exception as e:
            response = f"⚠️ An error occurred: {e}"