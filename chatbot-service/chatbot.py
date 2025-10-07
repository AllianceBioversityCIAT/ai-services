import os
import re
import uuid
import hashlib
import requests
import streamlit as st
from datetime import datetime, timezone
# from app.llm.vectorize_os import run_chatbot
from app.llm.agents import run_agent_chatbot
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import KNOWLEDGE_BASE
from app.utils.s3.upload_file_to_s3 import upload_file_to_s3

memory_id = KNOWLEDGE_BASE['memory_id']
MEMORY_ID = hashlib.sha256(memory_id.encode()).hexdigest()

logger = get_logger()

API_BASE_URL = "http://localhost:8001"

st.set_page_config(page_title="AICCRA chatbot", page_icon="🤖", layout="wide")
st.title("🤖 AI Assistant for AICCRA")


def track_ai_interaction(user_input: str, ai_output: str, context: dict = None, 
                        response_time: float = None, feedback_type: str = None, 
                        feedback_comment: str = None, update_mode: bool = False, 
                        interaction_id: str = None):
    """Track AI interaction or update with feedback."""
    try:
        interaction_data = {
            "user_id": MEMORY_ID,
            "session_id": st.session_state.session_id,
            "ai_output": ai_output,
            "service_name": "chatbot",
            "platform": "AICCRA",
            "update_mode": update_mode
        }
        
        # Add user_input only for new interactions (not updates)
        if not update_mode:
            interaction_data["user_input"] = user_input
        
        # Add interaction_id for updates
        if update_mode and interaction_id:
            interaction_data["interaction_id"] = interaction_id
        
        # Add feedback data if provided
        if feedback_type:
            interaction_data["feedback_type"] = feedback_type
        if feedback_comment:
            interaction_data["feedback_comment"] = feedback_comment
        
        # Add context and performance data
        if context:
            enhanced_context = {
                "filters_applied": context,
                "session_length": len(st.session_state.messages)
            }
            interaction_data["context"] = enhanced_context
        
        if response_time:
            interaction_data["response_time_seconds"] = response_time
        
        response = requests.post(
            f"{API_BASE_URL}/api/interactions",
            json=interaction_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            interaction_id = result.get('interaction_id')
            if update_mode:
                logger.info(f"✅ Feedback submitted successfully for interaction: {interaction_id}")
            else:
                logger.info(f"✅ Interaction tracked successfully: {interaction_id}")
            return True, interaction_id
        else:
            try:
                error_detail = response.json()
                error_message = error_detail.get('details', 'Unknown error')
            except:
                error_message = response.text
            logger.error(f"❌ Interaction tracking failed: {error_message}")
            return False, error_message
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error tracking interaction: {e}")
        return False, f"Network error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ Unexpected error tracking interaction: {e}")
        return False, f"Unexpected error: {str(e)}"
    

def start_new_session():
    """Limpia el historial de conversación e inicia una nueva sesión"""
    st.session_state.messages = []
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.show_feedback_area = False
    if "feedback_submitted" in st.session_state:
        del st.session_state.feedback_submitted
    if "last_interaction_id" in st.session_state:
        del st.session_state.last_interaction_id
    logger.info(f"🔄 New session started: {st.session_state.session_id}")
    st.rerun()


st.markdown("""
Welcome to your intelligent assistant for **AICCRA** (Accelerating Impacts of CGIAR Climate Research for Africa) data exploration. 

**How it works:**
- 🧠 **Memory-enabled**: Remembers your conversation and can answer follow-up questions
- 🎯 **Contextual responses**: Builds upon previous questions for more comprehensive answers  
- 🔍 **Smart filtering**: Use the sidebar filters to focus on specific data subsets
- 📊 **Data-driven**: Provides insights from AICCRA's deliverables, innovations, contributions, and impact reports

**Get started** by asking questions about clusters, indicators, innovations, or any AICCRA activities!
""")


# mode = st.radio(
#     "Choose interaction style:", 
#     [
#         "💬 Conversational (with memory & follow-ups)", 
#         "🔍 Quick Search (specific questions only)"
#     ], 
#     index=0)

# if mode == "💬 Conversational (with memory & follow-ups)":
#     st.caption("🧠 **Recommended**: Remembers your conversation, can answer follow-up questions, and provides contextual responses")
# elif mode == "🔍 Quick Search (specific questions only)":
#     st.caption("⚡ **Quick queries**: Best for specific, one-time questions about AICCRA data")


if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

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
        pdo = [f"PDO Indicator {i}" for i in range(1, 6)]
        ipi = [
            "IPI 1.1", "IPI 1.2", "IPI 1.3", "IPI 1.4",
            "IPI 2.1", "IPI 2.2", "IPI 2.3", "IPI 2.4",
            "IPI 3.1", "IPI 3.2", "IPI 3.3", "IPI 3.4", "IPI 3.5",
        ]

    return base + pdo + ipi

phase, indicator, section = "All phases", "All indicators", "All sections"


with st.sidebar:
    st.subheader("Filters")
    phase = st.selectbox("Phase", ["All phases", "AWPB 2021", "Progress 2021", "AR 2021", "AWPB 2022", "Progress 2022", "AR 2022", "AWPB 2023", "Progress 2023", "AR 2023", "AWPB 2024", "Progress 2024", "AR 2024", "AWPB 2025", "Progress 2025", "AR 2025"])
    indicator_options = get_indicator_options(get_year_from_phase(phase))
    indicator = st.selectbox("Indicator", indicator_options, index=0)
    section = st.selectbox("Section", ["All sections", "Deliverables", "OICRs", "Innovations", "Contributions"])
    st.caption("Apply filters to focus the AI assistant on specific data subsets.")
    
    st.divider()
    st.subheader("Session Controls")
    
    if st.session_state.messages:
        messages_count = len([msg for msg in st.session_state.messages if msg["role"] == "user"])
        st.caption(f"💬 Current session: {messages_count} questions asked")
        st.caption(f"🆔 Session ID: `{st.session_state.session_id[:8]}...`")
    
    if st.button("🔄 Start New Session", 
                 type="primary", 
                 help="Clear conversation history and start fresh",
                 use_container_width=True):
        start_new_session()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


user_input = st.chat_input("Ask about your AICCRA data, request reports, or get insights…☺️")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.feedback_submitted = False

    if phase == "All phases" or indicator == "All indicators" or section == "All sections":
        st.toast("💡 Tip: Your answers will be more precise if you apply filters from the sidebar.")
    
    start_time = datetime.now()

    with st.chat_message("user"):
        st.markdown(user_input)
    
    with st.spinner("Thinking..."):
        try:
            # if mode == "🔍 Quick Search (specific questions only)":
            #     response_stream = run_chatbot(user_input, phase=phase, indicator=indicator, section=section)
            # elif mode == "💬 Conversational (with memory & follow-ups)":
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
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            st.session_state.last_response_time = response_time

            # Track the AI interaction in the database
            filters_applied = {
                "phase": phase,
                "indicator": indicator,
                "section": section
            }
            
            success, interaction_id = track_ai_interaction(
                user_input=user_input,
                ai_output=full_response,
                context=filters_applied,
                response_time=response_time
            )
            
            if success:
                st.session_state.last_interaction_id = interaction_id
                logger.info(f"✅ Interaction tracked with ID: {interaction_id}")
            else:
                logger.error(f"❌ Failed to track interaction: {interaction_id}")

            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            full_response = f"⚠️ An error occurred: {e}"
            
            with st.chat_message("assistant"):
                st.markdown(full_response)

            # Track error interaction
            try:
                track_ai_interaction(
                    user_input=user_input,
                    ai_output=full_response,
                    context={"error": True, "error_message": str(e)}
                )
            except:
                logger.error("Failed to track error interaction")

            st.session_state.messages.append({"role": "assistant", "content": full_response})

if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":

    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

    with col5:
        if st.button("💾 Export Chat", 
                     key="export_chat",
                     help="Download conversation history",
                     type="primary"):
            chat_content = ""
            for i, msg in enumerate(st.session_state.messages):
                role = "User" if msg["role"] == "user" else "Assistant"
                chat_content += f"{role}: {msg['content']}\n\n"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📄 Download",
                data=chat_content,
                file_name=f"aiccra_chat_{timestamp}.txt",
                mime="text/plain",
                key="download_chat"
            )

    st.divider()
    
    if "show_feedback_area" not in st.session_state:
        st.session_state.show_feedback_area = False
    
    st.markdown("***Give feedback on this response*** :white_check_mark:")
    feedback_ack = st.empty()
    
    last_user_msg = ""
    last_ai_response = ""
    
    if len(st.session_state.messages) >= 2:
        last_ai_response = st.session_state.messages[-1]["content"]
        last_user_msg = st.session_state.messages[-2]["content"]
    
    col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12, col13, col14 = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    with col1:
        if st.button("👍", key="thumbs_up"):
            if hasattr(st.session_state, 'last_interaction_id'):
                success, message = track_ai_interaction(
                    user_input="",  # Not needed for updates
                    ai_output="",   # Not needed for updates
                    feedback_type="positive",
                    update_mode=True,
                    interaction_id=st.session_state.last_interaction_id
                )

                if success:
                    st.session_state.show_feedback_area = False
                    feedback_ack.success("✅ Thanks for your positive feedback!")
                else:
                    feedback_ack.error(f"❌ Error submitting feedback: {message}")
            else:
                feedback_ack.error("❌ No interaction ID found. Please try again.")
    
    with col2:
        if st.button("👎", key="thumbs_down"):
            st.session_state.show_feedback_area = True

    if st.session_state.show_feedback_area:
        with st.form("feedback_form", clear_on_submit=True):
            feedback_comment = st.text_area("\* Tell us what went wrong 👇", placeholder="Any suggestions or issues?")
            submitted = st.form_submit_button("Submit feedback", type="primary")
            
            if submitted and feedback_comment:
                if hasattr(st.session_state, 'last_interaction_id'):
                    success, message = track_ai_interaction(
                        user_input="",  # Not needed for updates
                        ai_output="",   # Not needed for updates
                        feedback_type="negative",
                        feedback_comment=feedback_comment,
                        update_mode=True,
                        interaction_id=st.session_state.last_interaction_id
                    )
                    
                    if success:
                        st.session_state.feedback_submitted = True
                        st.success("✅ Feedback submitted successfully. Thank you for helping us improve!")
                        st.session_state.show_feedback_area = False
                    else:
                        st.error(f"❌ Failed to submit feedback: {message}")
                        logger.error(f"Failed to submit feedback via API: {message}")
                else:
                    st.error("❌ No interaction ID found. Please try again.")