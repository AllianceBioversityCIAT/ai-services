import os
import re
import uuid
import hashlib
import streamlit as st
from datetime import datetime, timezone
from app.llm.vectorize_os import run_chatbot
from app.llm.agents import run_agent_chatbot
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import KNOWLEDGE_BASE
from app.utils.s3.upload_file_to_s3 import upload_file_to_s3


memory_id = KNOWLEDGE_BASE['memory_id']
MEMORY_ID = hashlib.sha256(memory_id.encode()).hexdigest()

logger = get_logger()

st.set_page_config(page_title="AICCRA chatbot", page_icon="🤖", layout="wide")
st.title("🤖 AICCRA Assistant")
mode = st.radio(
    "Choose interaction style:", 
    [
        "💬 Conversational (with memory & follow-ups)", 
        "🔍 Quick Search (specific questions only)"
    ], 
    index=0)

if mode == "💬 Conversational (with memory & follow-ups)":
    st.caption("🧠 **Recommended**: Remembers your conversation, can answer follow-up questions, and provides contextual responses")
elif mode == "🔍 Quick Search (specific questions only)":
    st.caption("⚡ **Quick queries**: Best for specific, one-time questions about AICCRA data")

## --- Initial status of messages ---
if "messages" not in st.session_state:
    st.session_state.messages = []

## --- Session ID for agents ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

## --- Status to show/hide filters ---
if "show_filters" not in st.session_state:
    st.session_state.show_filters = True

def toggle_filters():
    st.session_state.show_filters = not st.session_state.show_filters


def get_year_from_phase(phase_label: str):
    """Extract year from phase label like 'AWPB 2024'. Returns int year or None for 'All phases'."""
    if phase_label == "All phases":
        return None
    match = re.search(r"(20\d{2})$", phase_label)
    return int(match.group(1)) if match else None


def get_indicator_options(year: int | None):
    """Return the indicator options according to the specified year.
    If year is None (All phases), return the union of all indicators across years.
    """
    base = ["All indicators"]

    if year in (2021, 2022, 2023):
        pdo = [f"PDO Indicator {i}" for i in range(1, 4)]
        ipi = [
            "IPI 1.1", "IPI 1.2", "IPI 1.3",
            "IPI 2.1", "IPI 2.2", "IPI 2.3", "IPI 2.4",
            "IPI 3.1", "IPI 3.2", "IPI 3.3", "IPI 3.4", "IPI 3.5",
        ]
    elif year in (2024, 2025):
        pdo = [f"PDO Indicator {i}" for i in range(1, 6)]
        ipi = [
            "IPI 1.1", "IPI 1.2", "IPI 1.3", "IPI 1.4",
            "IPI 2.1", "IPI 2.2", "IPI 2.3",
            "IPI 3.1", "IPI 3.2", "IPI 3.3", "IPI 3.4",
        ]
    else:
        # Union of all indicators when year is None (All phases) or unknown
        pdo = [f"PDO Indicator {i}" for i in range(1, 6)]
        ipi = [
            "IPI 1.1", "IPI 1.2", "IPI 1.3", "IPI 1.4",
            "IPI 2.1", "IPI 2.2", "IPI 2.3", "IPI 2.4",
            "IPI 3.1", "IPI 3.2", "IPI 3.3", "IPI 3.4", "IPI 3.5",
        ]

    return base + pdo + ipi


phase, indicator, section = "All phases", "All indicators", "All sections"

## --- HISTORY ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

with st.sidebar:
    st.subheader("Filters")
    phase = st.selectbox("Phase", ["All phases", "AWPB 2021", "Progress 2021", "AR 2021", "AWPB 2022", "Progress 2022", "AR 2022", "AWPB 2023", "Progress 2023", "AR 2023", "AWPB 2024", "Progress 2024", "AR 2024", "AWPB 2025", "Progress 2025", "AR 2025"])
    indicator_options = get_indicator_options(get_year_from_phase(phase))
    indicator = st.selectbox("Indicator", indicator_options, index=0)
    section = st.selectbox("Section", ["All sections", "Deliverables", "OICRs", "Innovations", "Contributions"])
    st.caption("Apply filters to focus the AI assistant on specific data subsets.")

user_input = st.chat_input("Ask about your AICCRA data, request reports, or get insights…☺️")

if user_input:
    ## --- Save user message ---
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.feedback_submitted = False

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    file_name = f"interaction_{timestamp}.txt"
    local_path = os.path.join(os.getcwd(), "chat_logs", file_name)
    s3_key = f"aiccra/chatbot/chat_logs/{file_name}"
    st.session_state.feedback_local_path = local_path
    st.session_state.feedback_s3_key = s3_key

    if phase == "All phases" or indicator == "All indicators" or section == "All sections":
        st.toast("💡 Tip: Your answers will be more precise if you apply filters from the sidebar.")

    with st.chat_message("user"):
        st.markdown(user_input)
    
    with st.spinner("Thinking..."):
        try:
            if mode == "🔍 Quick Search (specific questions only)":
                response_stream = run_chatbot(user_input, phase=phase, indicator=indicator, section=section)
            elif mode == "💬 Conversational (with memory & follow-ups)":
                response_stream = run_agent_chatbot(
                    user_input,
                    phase=phase,
                    indicator=indicator,
                    section=section,
                    session_id=st.session_state.session_id,
                    memory_id=MEMORY_ID
                )
    
            full_response = ""
            first_chunk = True

            for chunk in response_stream:
                if first_chunk:
                    spinner_placeholder = st.empty()
                    spinner_placeholder.empty()
                    assistant_block = st.chat_message("assistant")
                    response_placeholder = assistant_block.empty()
                    first_chunk = False

                full_response += chunk
                response_placeholder.markdown(full_response)

            st.session_state.messages.append({"role": "assistant", "content": full_response})
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            with open(local_path, "w", encoding="utf-8") as f:
                f.write(f"User:\n{user_input}\n\nAssistant:\n{full_response}")

            upload_file_to_s3(s3_key, local_path)
            os.remove(local_path)

        except Exception as e:
            full_response = f"⚠️ An error occurred: {e}"
            
            with st.chat_message("assistant"):
                st.markdown(full_response)

            st.session_state.messages.append({"role": "assistant", "content": full_response})


if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
    if "show_feedback_area" not in st.session_state:
        st.session_state.show_feedback_area = False
    
    st.markdown("***Give feedback on this response*** :white_check_mark:")
    feedback_ack = st.empty()
    col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12, col13, col14 = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    with col1:
        if st.button("👍", key="thumbs_up"):
            st.session_state.show_feedback_area = False
            feedback_ack.success("Thanks for your feedback!")
    with col2:
        if st.button("👎", key="thumbs_down"):
            st.session_state.show_feedback_area = True

    if st.session_state.show_feedback_area:
        with st.form("feedback_form", clear_on_submit=True):
            feedback = st.text_area("Tell us what went wrong 👇", placeholder="Any suggestions or issues?")
            submitted = st.form_submit_button("Submit feedback", type="primary")
            if submitted and feedback:
                try:
                    st.session_state.feedback_submitted = True
                    with open(st.session_state.feedback_local_path, "w", encoding="utf-8") as f:
                        f.write(
                            f"User:\n{st.session_state.messages[-2]['content']}\n\nAssistant:\n{st.session_state.messages[-1]['content']}\n\nFeedback:\n{feedback}"
                        )
                    upload_file_to_s3(st.session_state.feedback_s3_key, st.session_state.feedback_local_path)
                    os.remove(st.session_state.feedback_local_path)

                    st.success("✅ Feedback submitted and saved.")
                    st.session_state.show_feedback_area = False

                except Exception as e:
                    st.error("❌ Failed to save feedback.")
                    logger.error(f"Failed to save feedback: {e}")