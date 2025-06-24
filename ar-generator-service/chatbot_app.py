import streamlit as st
from app.llm.vectorize_db import run_pipeline
from app.llm.knowledge_base import query_knowledge_base
from app.llm.vectorize_os import run_pipeline as run_pipeline_os

st.set_page_config(page_title="AICCRA App", page_icon="🌍")

st.title("🌍 AICCRA App")

mode = st.radio("Select the mode of use:", ["AICCRA Chatbot", "AICCRA Report Generator"])

## Chatbot
if mode == "AICCRA Chatbot":
    st.header("🤖 Chatbot AICCRA")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("What do you want to know?☺️")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        with st.spinner("Thinking..."):
            try:
                # response = query_knowledge_base(user_input)
                response_stream = query_knowledge_base(user_input)
                full_response = ""
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    for chunk in response_stream:
                        full_response += chunk
                        response_placeholder.markdown(full_response)
            except Exception as e:
                # response = f"⚠️ An error occurred: {e}"
                full_response = f"⚠️ An error occurred: {e}"
                with st.chat_message("assistant"):
                    st.markdown(full_response)

        # st.session_state.messages.append({"role": "assistant", "content": response})
        # with st.chat_message("assistant"):
        #     st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})

## Report Generator
elif mode == "AICCRA Report Generator":
    st.header("📄 AICCRA Report Generator")

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
    selected_year = st.selectbox("Select a year:", [2021, 2022, 2023, 2024, 2025])

    if st.button("Generate report"):
        with st.spinner("Generating report..."):
            try:
                # response = query_knowledge_base(selected_indicator, selected_year)
                
                ## response_stream = query_knowledge_base(selected_indicator, selected_year)
                ## response_stream = run_pipeline_os(selected_indicator, selected_year)
                response_stream = run_pipeline(selected_indicator, selected_year)
                full_response = ""
                report_placeholder = st.empty()
                for chunk in response_stream:
                    full_response += chunk
                    report_placeholder.markdown(full_response)
            except Exception as e:
                # response = f"⚠️ Ocurrió un error: {e}"
                full_response = f"⚠️ Ocurrió un error: {e}"
                report_placeholder = st.empty()
                report_placeholder.markdown(full_response)

        # st.markdown(response)