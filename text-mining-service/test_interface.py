# streamlit_app.py
import io
import json
import time
import boto3
import requests
import pandas as pd
import streamlit as st
from typing import Optional, List, Dict
from app.utils.config.config_util import S3
from botocore.exceptions import BotoCoreError, ClientError

# =========================
# Page config & styles
# =========================
st.set_page_config(
    page_title="Text Mining - Reporting Tool",
    page_icon="🧠",
    layout="wide",
)

st.markdown("""
<style>
.small { font-size: 0.85rem; opacity: 0.9; }
.muted { color: #6b7280; }
.stAlert { border-radius: 10px; }
.block-container { padding-top: 1.2rem; }
</style>
""", unsafe_allow_html=True)


# -------------------------
# Session state (persist results across reruns)
# -------------------------
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
if "last_payload" not in st.session_state:
    st.session_state["last_payload"] = None
if "last_df" not in st.session_state:
    st.session_state["last_df"] = None
if "last_elapsed" not in st.session_state:
    st.session_state["last_elapsed"] = None
if "last_source_id" not in st.session_state:
    st.session_state["last_source_id"] = None
# IMPORTANT: reset this to False on every run so downloads don't hide results
st.session_state["has_rendered_this_run"] = False

# =========================
# Helpers
# =========================
def list_s3_objects(bucket: str, prefix: str = "", max_items: int = 1000) -> List[str]:
    """List objects in S3; returns keys ordered by LastModified (desc)."""
    try:
        s3 = boto3.client(
            "s3", 
            aws_access_key_id=S3['aws_access_key'],
            aws_secret_access_key=S3['aws_secret_key'],
            region_name=S3['aws_region']
        )
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        items = []
        for page in pages:
            for obj in page.get("Contents", []):
                items.append((obj["Key"], obj["LastModified"]))
                if len(items) >= max_items:
                    break
        items.sort(key=lambda x: x[1], reverse=True)
        return [k for k, _ in items]
    except (BotoCoreError, ClientError) as e:
        st.error(f"❌ _S3 listing error: {e}_")
        return []


def normalize_results_to_df(result_json: Dict) -> pd.DataFrame:
    """
    Normalize the JSON output (with 'results': [...]) to a flat DataFrame.
    - Flattens 'geoscope'
    - Converts arrays/objects to readable strings
    - Keeps a friendly column order
    """
    results = result_json.get("results", [])
    if not isinstance(results, list):
        results = []

    df = pd.json_normalize(results, sep=".")

    def list_to_str(val):
        if isinstance(val, list):
            try:
                return ", ".join([
                    json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
                    for v in val
                ])
            except Exception:
                return json.dumps(val, ensure_ascii=False)
        return val

    for col in df.columns:
        df[col] = df[col].apply(list_to_str)

    first_cols = [
        "indicator",
        "title",
        "description",
        "keywords",
        "geoscope.level",
        "geoscope.sub_list",
        "training_type",
        "total_participants",
        "male_participants",
        "female_participants",
        "non_binary_participants",
        "delivery_modality",
        "start_date",
        "end_date",
        "length_of_training",
        "degree",
        "policy_type",
        "stage_in_policy_process",
        "evidence_for_stage",
        "short_title",
        "innovation_nature",
        "innovation_type",
        "assess_readiness",
        "anticipated_users",
        "organizations",
        "organization_type",
        "organization_sub_type",
        "alliance_main_contact_person_first_name",
        "alliance_main_contact_person_last_name",
    ]
    ordered = [c for c in first_cols if c in df.columns] + [c for c in df.columns if c not in first_cols]
    return df[ordered] if not df.empty else df


def extract_inner_results_json(raw: Dict) -> Dict:
    """
    Extracts the actual payload with 'results' from wrapper responses.
    Supports backends that return:
      { "content": [ {"type":"text", "text": "{...json...}"} ], ... }
    or direct { "text": "{...json...}" }.
    Returns a dict that ideally contains 'results': [...]
    """
    if isinstance(raw, dict) and "results" in raw:
        return raw

    content = raw.get("content")
    if isinstance(content, list):
        for item in content:
            text = item.get("text")
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and "results" in parsed:
                        return parsed
                except Exception:
                    continue

    text = raw.get("text")
    if isinstance(text, str):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "results" in parsed:
                return parsed
        except Exception:
            pass

    return {"results": []}


def _set_results(result: Dict, payload: Dict, df: pd.DataFrame, elapsed: float, source_id: str) -> None:
    st.session_state["last_result"] = result
    st.session_state["last_payload"] = payload
    st.session_state["last_df"] = df
    st.session_state["last_elapsed"] = elapsed
    st.session_state["last_source_id"] = source_id
    st.session_state["has_rendered_this_run"] = False  # ensure we can render after rerun


# Helper to clear persisted results
def _clear_results() -> None:
    st.session_state["last_result"] = None
    st.session_state["last_payload"] = None
    st.session_state["last_df"] = None
    st.session_state["last_elapsed"] = None
    st.session_state["last_source_id"] = None


def _render_results(result: Dict, df: pd.DataFrame, elapsed: float) -> None:
    st.success(f"Processed successfully! ⏱️ {elapsed:.2f}s")

    with st.expander("🔎 **Raw JSON output**", expanded=False):
        st.json(result)

    st.subheader("📊 Results")
    st.dataframe(df, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        json_bytes = json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            "⬇️ **Download JSON**",
            data=json_bytes,
            file_name="text_mining_result.json",
            mime="application/json",
            use_container_width=True
        )
    with c2:
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        st.download_button(
            "⬇️ **Download CSV**",
            data=csv_buf.getvalue(),
            file_name="text_mining_result.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.session_state["has_rendered_this_run"] = True


def post_to_api(
    base_url: str,
    bucket: str,
    token: str,
    environment_url: str,
    prompt: Optional[str] = None,
    key: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
    file_type: Optional[str] = None,
) -> Dict:
    """
    Call the FastAPI /process endpoint.
    - If file_bytes is present, send multipart with 'file'
    - Otherwise, send 'key'
    """
    url = base_url.rstrip("/") + "/prms/text_mining"
    
    headers = {
        'User-Agent': 'StreamlitApp/1.0',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    data = {
        "bucketName": bucket,
        "token": token,
        "environmentUrl": environment_url
    }

    if prompt is not None and prompt != "":
        data["prompt"] = prompt

    files = None
    if file_bytes is not None and file_name:
        files = {"file": (file_name, file_bytes, file_type or "application/octet-stream")}
    else:
        data["key"] = key or ""

    resp = requests.post(url, data=data, files=files, headers=headers, timeout=900)
    if resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
    return resp.json()

# =========================
# Sidebar
# =========================
st.sidebar.title("⚙️ Settings")
api_base_url = st.sidebar.text_input(
    "FastAPI Base URL",
    value="https://d3djd7q7g7v7di.cloudfront.net",
    help="Your FastAPI service URL (defaults to https://d3djd7q7g7v7di.cloudfront.net)."
)
bucket = st.sidebar.text_input("S3 Bucket", value="microservice-mining")
token = st.sidebar.text_input("Auth Token", value="", type="password")
environment_url = st.sidebar.text_input("Environment URL", value="https://management-allianceindicatorstest.ciat.cgiar.org/api/")

st.sidebar.markdown("---")
st.sidebar.caption("*AWS credentials are taken from your environment. Ensure `boto3` is authorized.*")

# =========================
# Main
# =========================
st.title("🧠 Text Mining - Interactive Test UI")
st.markdown(
    "<div class='muted'>Upload a document or select one from S3, send it to the text-mining service, and visualize results.</div>",
    unsafe_allow_html=True
)

st.markdown("######")
    
mode = st.radio(
    "**📄 Document source:**",
    options=["Upload file", "Select from S3"],
    horizontal=True
)

col_left, col_right = st.columns([2, 1])

selected_key = None
uploaded_file = None

with col_left:
    if mode == "Upload file":
        uploaded_file = st.file_uploader(
            "File type (_pdf, docx, txt, xlsx, xls, pptx_)",
            type=None,
            accept_multiple_files=False
        )
    else:
        with st.expander("S3 search options", expanded=True):
            prefix = st.text_input("Prefix (optional)", value="")
            refresh = st.button("🔄 Refresh list")

        if bucket:
            if "s3_keys_cache" not in st.session_state or refresh or st.session_state.get("last_prefix") != prefix:
                with st.spinner("Listing S3 objects..."):
                    st.session_state["s3_keys_cache"] = list_s3_objects(bucket, prefix)
                    st.session_state["last_prefix"] = prefix
            keys = st.session_state.get("s3_keys_cache", [])
            if keys:
                selected_key = st.selectbox(
                    "Select an object from S3",
                    options=keys,
                    index=0
                )
            else:
                st.info("_No objects found for this bucket/prefix._")

with col_right:
    st.markdown("####")
    run_btn = st.button("🚀 Process document", type="primary", use_container_width=True)
    st.caption("_Tip: Filter by prefix to quickly find your files._")

# =========================
# Main action
# =========================
if run_btn:
    if not bucket or not token or not environment_url:
        st.error("❌ _Please complete **S3 Bucket**, **Auth Token**, and **Environment URL** in the sidebar._")
    else:
        try:
            with st.spinner("Sending document to the service…"):
                t0 = time.time()

                if mode == "Upload file":
                    if not uploaded_file:
                        st.warning("⚠️ _You need to select a file to upload._")
                        st.stop()
                    file_bytes = uploaded_file.read()
                    result = post_to_api(
                        base_url=api_base_url,
                        bucket=bucket,
                        token=token,
                        environment_url=environment_url,
                        file_bytes=file_bytes,
                        file_name=uploaded_file.name,
                        file_type=uploaded_file.type
                    )
                else:
                    if not selected_key:
                        st.warning("⚠️ _You need to select an S3 object._")
                        st.stop()
                    result = post_to_api(
                        base_url=api_base_url,
                        bucket=bucket,
                        token=token,
                        environment_url=environment_url,
                        key=selected_key
                    )

                elapsed = time.time() - t0

            if isinstance(result, dict) and (result.get("status") == "error" or result.get("isError") is True):
                _clear_results()
                st.error(f"❌ _Service returned an error: {result.get('error') or result.get('message') or 'Unknown error'}_")
                st.stop()

            # Build a stable source identifier (only updates when user clicks Process)
            if mode == "Upload file" and uploaded_file is not None:
                source_id = f"upload::{uploaded_file.name}"
            elif mode == "Select from S3" and selected_key:
                source_id = f"s3::{selected_key}"
            else:
                source_id = "unknown"

            # Normalize and persist results in session_state
            try:
                payload = extract_inner_results_json(result)
                df = normalize_results_to_df(payload)
            except Exception as e:
                st.error(f"❌ _Failed to normalize output to table: {e}_")
                df = pd.DataFrame()

            if not df.empty:
                _set_results(result, payload, df, elapsed, source_id)
                _render_results(st.session_state["last_result"], st.session_state["last_df"], st.session_state["last_elapsed"])
            else:
                _clear_results()
                st.warning("⚠️ _No results to display (empty list or unexpected structure)._")

        except requests.exceptions.RequestException as e:
            _clear_results()
            st.error(f"❌ _Could not reach the API: {e}_")
        except Exception as e:
            _clear_results()
            st.exception(e)

# -------------------------
# Persist results across reruns (e.g., after clicking download buttons)
# -------------------------
if not st.session_state.get("has_rendered_this_run") and st.session_state.get("last_df") is not None:
    # Only render if we have previous results and haven't rendered them yet in this run
    _render_results(st.session_state["last_result"], st.session_state["last_df"], st.session_state["last_elapsed"])


# =========================
# Footer
# =========================
st.markdown("#")
st.markdown("---")
st.caption("© Text Mining Service - Demo UI. Built with ❤️ in Streamlit.")