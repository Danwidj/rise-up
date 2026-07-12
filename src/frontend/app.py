import sys
import os
import time
import contextlib
import tempfile
from pathlib import Path
import pandas as pd

import streamlit as st
from dotenv import load_dotenv

# src/frontend/app.py -> project root
root_path = Path(__file__).resolve().parent.parent.parent

# Load environment variables BEFORE importing modules that use them
env_path = root_path / ".env"
load_dotenv(dotenv_path=env_path)

if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

import r2
import video
import nim
from src.frontend import database

# Initialize database
database.init_db()

# Set Page Config
st.set_page_config(
    page_title="RISE UP - Video Analytics",
    page_icon="video",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Enterprise Light UI
st.markdown("""
<style>
    /* Global Styles & Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
        background-color: #F7F8FA !important;
        color: #171A1F !important;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E4E7EC !important;
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #667085 !important;
        font-size: 14px;
    }

    /* Headings override */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        color: #171A1F !important;
        font-weight: 600 !important;
    }

    /* Active & Inactive Sidebar Nav Button Styles */
    section[data-testid="stSidebar"] div.stButton > button {
        text-align: left !important;
        padding: 10px 16px !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        border-radius: 8px !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }

    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background-color: #F1F8E8 !important;
        color: #171A1F !important;
        border: 1px solid #76B900 !important;
        box-shadow: none !important;
        font-weight: 600 !important;
    }

    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #667085 !important;
        border: 1px solid #E4E7EC !important;
    }

    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover {
        background-color: #F7F8FA !important;
        color: #171A1F !important;
        border-color: #98A2B3 !important;
    }

    /* Primary and secondary main view button overrides */
    div[data-testid="stMainBlockContainer"] div.stButton > button[kind="primary"] {
        background-color: #76B900 !important;
        border: 1px solid #76B900 !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
        box-shadow: none !important;
    }

    div[data-testid="stMainBlockContainer"] div.stButton > button[kind="primary"]:hover {
        background-color: #5A8F00 !important;
        border-color: #5A8F00 !important;
    }

    div[data-testid="stMainBlockContainer"] div.stButton > button[kind="secondary"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E4E7EC !important;
        color: #171A1F !important;
        border-radius: 6px !important;
    }

    div[data-testid="stMainBlockContainer"] div.stButton > button[kind="secondary"]:hover {
        background-color: #F7F8FA !important;
        border-color: #98A2B3 !important;
    }

    /* Input and selectors styling */
    input, textarea, [data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E4E7EC !important;
        color: #171A1F !important;
        border-radius: 8px !important;
    }

    /* Badges */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: 600;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .status-verified { background-color: #F1F8E8; color: #16A34A; border: 1px solid rgba(22, 163, 74, 0.2); }
    .status-review { background-color: #FFFBEB; color: #D97706; border: 1px solid rgba(217, 119, 6, 0.2); }
    .status-unreviewed { background-color: #F3F4F6; color: #667085; border: 1px solid rgba(102, 112, 133, 0.2); }

    .sev-badge {
        display: inline-block;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 600;
        border-radius: 4px;
    }
    .sev-5 { background-color: #FEE2E2; color: #DC2626; }
    .sev-4 { background-color: #FFEDD5; color: #EA580C; }
    .sev-3 { background-color: #FEF3C7; color: #D97706; }
    .sev-2 { background-color: #ECFDF5; color: #16A34A; }
    .sev-1 { background-color: #F3F4F6; color: #667085; }

    /* Dashboard metric cards - plain white, no circle border artifacts */
    div[data-testid="stMainBlockContainer"] div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E4E7EC;
        border-radius: 10px;
        padding: 16px 20px;
    }

    /* Terminal output block */
    pre code {
        color: #171A1F !important;
        background-color: #F7F8FA !important;
        border: 1px solid #E4E7EC !important;
    }
</style>
""", unsafe_allow_html=True)

# Custom stdout Redirection class for Real-time Streaming in Streamlit
class StreamToStreamlit:
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.content = ""

    def write(self, text):
        self.content += text
        self.placeholder.code(self.content, language="text")
        st.session_state.last_analysis_result = self.content

    def flush(self):
        pass

@contextlib.contextmanager
def st_stdout(placeholder):
    sys.stdout.flush()
    old_stdout = sys.stdout
    sys.stdout = StreamToStreamlit(placeholder)
    try:
        yield
    finally:
        sys.stdout.flush()
        sys.stdout = old_stdout

def timestamp_to_seconds(ts_str: str) -> int:
    try:
        parts = list(map(int, ts_str.split(':')))
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return int(ts_str)
    except Exception:
        return 0

# Check credentials
missing_credentials = []
for var in ["R2_BUCKET", "R2_ACCOUNT_ID", "R2_ACCESS_KEY", "R2_SECRET_KEY"]:
    if not os.getenv(var):
        missing_credentials.append(var)

# Initialize Session State
if "current_page" not in st.session_state:
    st.session_state.current_page = "reports"
if "selected_report_id" not in st.session_state:
    st.session_state.selected_report_id = None
# "analyze" sub-view state: None = list, "new" = upload+analyze form
if "reports_subview" not in st.session_state:
    st.session_state.reports_subview = "list"
if "analyze_video_key" not in st.session_state:
    st.session_state.analyze_video_key = None
if "search_prompt" not in st.session_state:
    st.session_state.search_prompt = "Describe this video in detail."
if "last_analysis_result" not in st.session_state:
    st.session_state.last_analysis_result = None

# --- TOP HEADER BAR ---
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.markdown("""
    <div style="margin-top: 10px;">
        <span style="font-size: 28px; font-weight: 700; color: #171A1F; letter-spacing: -0.5px;">RISE UP</span>
        <span style="font-size: 14px; font-weight: 500; color: #76B900; margin-left: 8px; border: 1px solid #76B900; padding: 2px 8px; border-radius: 4px;">NVIDIA POWERED</span>
        <div style="font-size: 14px; color: #667085; margin-top: 4px;">AI-Powered Post-Incident Video Analysis and Intelligent Reporting Platform</div>
    </div>
    """, unsafe_allow_html=True)
with header_col2:
    st.image("src/frontend/assets/nvidia_logo_horizontal.png", use_container_width=True)

st.markdown("<hr style='margin: 12px 0 24px 0; border: 0; border-top: 1px solid #E4E7EC;'/>", unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 16px 0;">
        <span style="font-size: 16px; font-weight: 700; color: #171A1F;">Navigation</span>
    </div>
    """, unsafe_allow_html=True)

    nav_items = [
        ("reports", "Incident Reports"),
        ("dashboard", "Analytics Dashboard"),
    ]

    for page_key, label in nav_items:
        is_active = (st.session_state.current_page == page_key)
        if st.button(
            label,
            key=f"nav_{page_key}",
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            st.session_state.current_page = page_key
            st.session_state.selected_report_id = None
            st.session_state.reports_subview = "list"
            st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="font-size: 12px; color: #98A2B3; text-align: center; margin-top: 12px;">
        <b>SMU IS483 Group Project</b><br>Rise Up
    </div>
    """, unsafe_allow_html=True)

# --- CREDENTIAL GUARD ---
if missing_credentials:
    st.error(f"Missing Cloudflare R2 configuration: {', '.join(missing_credentials)}")
    st.warning("Please configure your `.env` file in the project root with the correct credentials.")
    st.stop()

# =============================================================================
# PAGE 1: INCIDENT REPORTS
#   Sub-views: "list" | "detail" | "analyze"
# =============================================================================
if st.session_state.current_page == "reports":

    # ------------------------------------------------------------------
    # SUB-VIEW: ANALYZE (AI analysis on a specific video)
    # ------------------------------------------------------------------
    if st.session_state.reports_subview == "analyze":
        selected_video = st.session_state.analyze_video_key

        # Back button
        if st.button("Back to Incident Reports"):
            st.session_state.reports_subview = "list"
            st.session_state.analyze_video_key = None
            st.session_state.last_analysis_result = None
            st.rerun()

        st.markdown(f"### AI Analysis: `{selected_video}`")

        col_play, col_setup = st.columns([1, 1], gap="large")

        with col_play:
            st.markdown("##### Video Preview")
            try:
                video_url = r2.generate_presigned_url(selected_video)
                st.video(video_url)
                st.caption(f"Source: `{selected_video}`")
            except Exception as e:
                st.error(f"Failed to stream video: {e}")

        with col_setup:
            st.markdown("##### Analysis Parameters")

            st.write("Example Prompts:")
            chip_col1, chip_col2 = st.columns(2)
            with chip_col1:
                if st.button("robbery / violence", use_container_width=True):
                    st.session_state.search_prompt = "Is there any robbery, fighting, physical violence, or safety concerns in this video? Focus on when it happens and who is involved."
                if st.button("stealing / theft", use_container_width=True):
                    st.session_state.search_prompt = "Look for any suspicious shoplifting, stealing, or concealment of items in this footage. Detail the actions."
            with chip_col2:
                if st.button("suspicious activity", use_container_width=True):
                    st.session_state.search_prompt = "Analyze the video for general anomalies, suspicious behaviors, or trespassing. Provide timestamps."
                if st.button("timeline overview", use_container_width=True):
                    st.session_state.search_prompt = "Write a concise timeline of events in this clip. What actions are happening?"

            prompt = st.text_area("Analysis Prompt:", value=st.session_state.search_prompt, height=90)
            think = st.toggle("Enable Reasoning (/think mode)", value=True)

            with st.expander("Advanced NVIDIA API Settings", expanded=False):
                max_tokens = st.slider("Max Output Tokens", 1024, 65536, 65536, step=1024)
                temperature = st.slider("Temperature", 0.0, 1.0, 0.6 if think else 0.2, step=0.1)
                reasoning_budget = st.slider("Reasoning Budget (tokens)", 1024, 32768, 16384, step=1024)

            st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
            analyze_button = st.button("Run AI Video Analysis", use_container_width=True)

        if analyze_button:
            if not os.getenv("NVIDIA_API_KEY"):
                st.error("Cannot perform analysis: NVIDIA_API_KEY is not set.")
            else:
                st.markdown("---")
                st.subheader("Live Model Generation Output")

                temp_local_file = Path(f"temp_{Path(selected_video).name}")
                temp_compressed_file = Path(f"temp_compressed_{Path(selected_video).name}")
                status_box = st.empty()
                terminal_placeholder = st.empty()

                try:
                    status_box.info("Downloading video from Cloudflare R2...")
                    r2.download_file(selected_video, temp_local_file)

                    status_box.info("Probing video constraints...")
                    info = video.probe_video(str(temp_local_file))
                    problems = video.check_constraints(info)

                    if problems:
                        st.error("Validation failed:")
                        for prob in problems:
                            st.markdown(f"- {prob}")
                        st.stop()

                    active_video_file = temp_local_file
                    if info.size_bytes > 19000000:
                        status_box.warning("Video exceeds payload size limit. Compressing...")
                        video.compress_video(str(temp_local_file), str(temp_compressed_file), info.duration_s)
                        active_video_file = temp_compressed_file

                    status_box.info("Encoding video payload...")
                    video_base64_url = video.to_data_url(str(active_video_file))

                    status_box.success("Streaming output from NVIDIA Nemotron Omni...")
                    with st_stdout(terminal_placeholder):
                        nim.describe_video(
                            video_url=video_base64_url,
                            prompt=prompt,
                            api_key=os.getenv("NVIDIA_API_KEY"),
                            think=think,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            reasoning_budget=reasoning_budget,
                            stream=True
                        )
                    status_box.success("Analysis completed successfully!")

                except Exception as e:
                    st.error(f"An error occurred during analysis: {e}")
                finally:
                    for f in (temp_local_file, temp_compressed_file):
                        if f.exists():
                            try:
                                f.unlink()
                            except Exception:
                                pass

        # Save result as a new incident report
        if st.session_state.last_analysis_result:
            st.markdown("---")
            st.markdown("#### Create Incident Report from AI Analysis")
            st.write("Review the details and save the result to the incident database.")

            with st.form("save_report_form"):
                save_type = st.selectbox("Detected Incident Type", ["Robbery", "Fighting", "Shooting", "Stealing", "Abuse", "Vandalism", "Suspicious Behavior", "Normal Video"])
                save_loc = st.text_input("Incident Location / Camera ID", value="Camera Lobby Area")

                c_ts1, c_ts2 = st.columns(2)
                with c_ts1:
                    save_start = st.text_input("Start Timestamp (e.g. 00:10)", value="00:05")
                with c_ts2:
                    save_end = st.text_input("End Timestamp (e.g. 00:40)", value="00:30")

                save_sev = st.slider("Severity Level", 1, 5, value=3)
                save_conf = st.slider("Confidence score (%)", 0.0, 100.0, value=95.0)
                save_poi = st.text_input("Person of Interest (POI) description", value="Male in dark clothing")
                save_inst = st.text_input("Instrument / Weapon Used", value="None")
                save_summary = st.text_area("Incident summary text", value=st.session_state.last_analysis_result, height=120)
                save_status = st.selectbox("Status", ["Unreviewed", "Under Review", "Verified"])

                submit_save = st.form_submit_button("Save to Incident Database")

            if submit_save:
                new_id = database.add_report(
                    selected_video, save_type, save_start, save_end,
                    save_sev, save_conf, save_summary, save_poi,
                    save_inst, save_loc, save_status
                )
                st.success(f"Incident saved as Report #{new_id}!")
                st.session_state.last_analysis_result = None
                st.session_state.reports_subview = "list"
                st.session_state.analyze_video_key = None
                time.sleep(1)
                st.rerun()

    # ------------------------------------------------------------------
    # SUB-VIEW: DETAIL (view + edit a single report)
    # ------------------------------------------------------------------
    elif st.session_state.selected_report_id is not None:
        report = database.get_report_by_id(st.session_state.selected_report_id)
        if report is None:
            st.session_state.selected_report_id = None
            st.rerun()

        if st.button("Back to Incident Reports"):
            st.session_state.selected_report_id = None
            st.rerun()

        st.markdown(f"### Incident Report #{report['id']}")

        col_video, col_review = st.columns([3, 2], gap="large")

        with col_video:
            st.markdown("##### Video Recording")
            try:
                video_url = r2.generate_presigned_url(report['video_key'])
                start_seconds = timestamp_to_seconds(report['start_timestamp'])
                if "video_playback_start" not in st.session_state or st.session_state.get("playback_report_id") != report['id']:
                    st.session_state.video_playback_start = start_seconds
                    st.session_state.playback_report_id = report['id']

                st.video(video_url, start_time=st.session_state.video_playback_start)
                st.caption(f"Asset: `{report['video_key']}`")

                ctrl1, ctrl2 = st.columns([2, 1])
                with ctrl1:
                    if st.button("Play from Incident Start", use_container_width=True):
                        st.session_state.video_playback_start = start_seconds
                        st.rerun()
                with ctrl2:
                    st.info(f"Start: {report['start_timestamp']}")

                st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E4E7EC; border-radius: 8px; padding: 12px; margin-top: 16px;">
                    <div style="font-size: 13px; font-weight: 600; color: #667085; margin-bottom: 8px;">Timeline Window ({report['start_timestamp']} - {report['end_timestamp']})</div>
                    <div style="height: 12px; background-color: #E4E7EC; border-radius: 6px; position: relative; width: 100%;">
                        <div style="position: absolute; left: 15%; width: 50%; height: 100%; background-color: #76B900; border-radius: 6px;"></div>
                        <div style="position: absolute; left: 15%; height: 16px; width: 2px; background-color: #DC2626; top: -2px;"></div>
                        <div style="position: absolute; left: 65%; height: 16px; width: 2px; background-color: #DC2626; top: -2px;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #98A2B3; margin-top: 6px;">
                        <span>00:00 (Start)</span>
                        <span>Incident Range</span>
                        <span>End of Clip</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Button to re-run AI analysis on this video
                st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
                if st.button("Run AI Analysis on This Video", use_container_width=True):
                    st.session_state.analyze_video_key = report['video_key']
                    st.session_state.selected_report_id = None
                    st.session_state.reports_subview = "analyze"
                    st.rerun()

            except Exception as e:
                st.error(f"Error playing video stream: {e}")

        with col_review:
            st.markdown("##### Incident Metadata and Verification")

            tag_col1, tag_col2 = st.columns(2)
            with tag_col1:
                st.markdown(f"""
                <div style="border: 1px solid #E4E7EC; border-radius: 8px; padding: 12px; text-align: center; background-color: #F7F8FA; height: 100px; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 10px; color: #98A2B3; font-weight: 700; text-transform: uppercase;">Person of Interest</div>
                    <div style="font-size: 12px; font-weight: 600; color: #171A1F; margin-top: 6px;">{report['poi_detected'] or 'None'}</div>
                </div>
                """, unsafe_allow_html=True)
            with tag_col2:
                st.markdown(f"""
                <div style="border: 1px solid #E4E7EC; border-radius: 8px; padding: 12px; text-align: center; background-color: #F7F8FA; height: 100px; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 10px; color: #98A2B3; font-weight: 700; text-transform: uppercase;">Instrument / Object</div>
                    <div style="font-size: 12px; font-weight: 600; color: #171A1F; margin-top: 6px;">{report['instruments_detected'] or 'None'}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

            with st.form("edit_report_form"):
                incident_types = ["Robbery", "Fighting", "Shooting", "Stealing", "Abuse", "Vandalism", "Suspicious Behavior", "Normal Video"]
                edit_type = st.selectbox(
                    "Incident Type", incident_types,
                    index=incident_types.index(report['incident_type']) if report['incident_type'] in incident_types else 0
                )
                edit_loc = st.text_input("Location / Camera Area", value=report['location'])

                col_ts1, col_ts2 = st.columns(2)
                with col_ts1:
                    edit_start = st.text_input("Start Timestamp", value=report['start_timestamp'])
                with col_ts2:
                    edit_end = st.text_input("End Timestamp", value=report['end_timestamp'])

                edit_sev = st.slider("Severity Level", 1, 5, value=int(report['severity']))
                edit_conf = st.slider("Confidence Score (%)", 0.0, 100.0, value=float(report['confidence_score']))
                edit_summary = st.text_area("Incident Description Summary", value=report['summary'], height=100)

                col_poi_text, col_inst_text = st.columns(2)
                with col_poi_text:
                    edit_poi = st.text_input("Person of Interest Description", value=report['poi_detected'])
                with col_inst_text:
                    edit_inst = st.text_input("Instrument / Object Detected", value=report['instruments_detected'])

                statuses = ["Verified", "Under Review", "Unreviewed"]
                edit_status = st.selectbox(
                    "Verification Status", statuses,
                    index=statuses.index(report['verification_status'])
                )

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    submit_edit = st.form_submit_button("Save Changes", use_container_width=True)
                with btn_col2:
                    confirm_delete = st.form_submit_button("Delete Report", use_container_width=True)

            if submit_edit:
                database.update_report(
                    report['id'], edit_type, edit_start, edit_end,
                    edit_sev, edit_conf, edit_summary, edit_poi,
                    edit_inst, edit_loc, edit_status
                )
                st.success("Changes saved successfully!")
                time.sleep(1)
                st.rerun()

            if confirm_delete:
                database.delete_report(report['id'])
                st.warning("Report deleted successfully.")
                st.session_state.selected_report_id = None
                time.sleep(1)
                st.rerun()

    # ------------------------------------------------------------------
    # SUB-VIEW: LIST (default — report cards + upload)
    # ------------------------------------------------------------------
    else:
        st.markdown("### Incident Reports Library")

        # Top action row: filters on left, upload button on right
        filter_col1, filter_col2, filter_col3, upload_col = st.columns([2, 1, 1, 1])
        with filter_col1:
            search_term = st.text_input("Search reports...", placeholder="Location, type, person, object...").strip()
        with filter_col2:
            type_filter = st.selectbox("Type", ["All Types", "Robbery", "Fighting", "Shooting", "Stealing", "Abuse", "Vandalism", "Suspicious Behavior"])
        with filter_col3:
            status_filter = st.selectbox("Status", ["All Statuses", "Verified", "Under Review", "Unreviewed"])
        with upload_col:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            show_upload = st.button("Upload New Video", use_container_width=True)

        # Upload panel (shown inline when button clicked)
        if show_upload:
            st.session_state.show_upload_panel = not st.session_state.get("show_upload_panel", False)

        if st.session_state.get("show_upload_panel", False):
            with st.container(border=True):
                st.markdown("**Upload surveillance footage to Cloudflare R2**")
                uploaded_file = st.file_uploader("Choose a local MP4 file", type=["mp4"])
                if uploaded_file is not None:
                    file_name = uploaded_file.name
                    up_col1, up_col2 = st.columns([3, 1])
                    with up_col1:
                        st.info(f"Ready to upload: `{file_name}`")
                    with up_col2:
                        if st.button("Confirm Upload", use_container_width=True):
                            with st.spinner("Uploading to Cloudflare R2..."):
                                try:
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                                        tmp_file.write(uploaded_file.read())
                                        tmp_path = tmp_file.name
                                    r2.upload_file(tmp_path, file_name)
                                    st.success(f"Uploaded as `{file_name}`!")
                                    # After upload, jump straight to analyze for this video
                                    st.session_state.analyze_video_key = file_name
                                    st.session_state.reports_subview = "analyze"
                                    st.session_state.show_upload_panel = False
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Upload failed: {e}")
                                finally:
                                    if 'tmp_path' in locals() and os.path.exists(tmp_path):
                                        os.unlink(tmp_path)

        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

        # Also allow selecting any existing R2 video to analyze directly
        with st.expander("Analyze an Existing Video from Library", expanded=False):
            try:
                with st.spinner("Fetching R2 library..."):
                    all_objects = r2.list_objects()
                r2_videos = [obj for obj in all_objects if obj.lower().endswith(".mp4")]
            except Exception as e:
                st.error(f"Failed to list R2 files: {e}")
                r2_videos = []

            if r2_videos:
                sel_col1, sel_col2 = st.columns([3, 1])
                with sel_col1:
                    pick_video = st.selectbox(f"Select a video ({len(r2_videos)} found)", r2_videos, key="library_picker")
                with sel_col2:
                    st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Analyze Selected", use_container_width=True):
                        st.session_state.analyze_video_key = pick_video
                        st.session_state.reports_subview = "analyze"
                        st.rerun()
            else:
                st.info("No videos found in R2 bucket.")

        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

        # Load and filter reports
        reports = database.get_all_reports()
        filtered_reports = []
        for r in reports:
            if search_term:
                search_lower = search_term.lower()
                haystack = f"{r['location']} {r['summary']} {r['poi_detected']} {r['instruments_detected']} {r['incident_type']}".lower()
                if search_lower not in haystack:
                    continue
            if type_filter != "All Types" and r['incident_type'] != type_filter:
                continue
            if status_filter != "All Statuses" and r['verification_status'] != status_filter:
                continue
            filtered_reports.append(r)

        if filtered_reports:
            for idx in range(0, len(filtered_reports), 3):
                row_cols = st.columns(3, gap="medium")
                for j in range(3):
                    if idx + j < len(filtered_reports):
                        r = filtered_reports[idx + j]
                        with row_cols[j]:
                            with st.container(border=True):
                                st.markdown(f"""
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <span class="status-badge status-{'verified' if r['verification_status']=='Verified' else 'review' if r['verification_status']=='Under Review' else 'unreviewed'}">{r['verification_status']}</span>
                                    <span style="font-size: 11px; color: #98A2B3; font-weight: 500;">Report #{r['id']}</span>
                                </div>
                                <h4 style="margin: 2px 0 6px 0; font-size: 16px;">{r['incident_type']}</h4>
                                <div style="font-size: 12px; color: #667085; margin-bottom: 12px;">
                                    <span style="margin-right: 12px;">Location: {r['location']}</span>
                                    <span>Time: {r['start_timestamp']} - {r['end_timestamp']}</span>
                                </div>
                                <p style="font-size: 13px; color: #667085; line-height: 1.5; height: 60px; overflow: hidden; margin-bottom: 12px;">
                                    {r['summary'][:110] + '...' if len(r['summary']) > 110 else r['summary']}
                                </p>
                                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #E4E7EC; padding-top: 12px; margin-bottom: 12px;">
                                    <span style="font-size: 12px; color: #667085;">Severity: <span class="sev-badge sev-{r['severity']}">{r['severity']}/5</span></span>
                                    <span style="font-size: 12px; color: #667085;">Confidence: <b>{r['confidence_score']:.1f}%</b></span>
                                </div>
                                """, unsafe_allow_html=True)

                                if st.button("View and Verify Details", key=f"select_rep_{r['id']}", use_container_width=True):
                                    st.session_state.selected_report_id = r['id']
                                    st.rerun()
        else:
            st.markdown("""
            <div style="text-align: center; padding: 60px 0; color: #98A2B3;">
                <div style="font-size: 32px; margin-bottom: 12px;">--</div>
                <div style="font-size: 16px; font-weight: 600; color: #667085;">No incident reports found</div>
                <div style="font-size: 14px; margin-top: 6px;">Try adjusting your filters or upload a new video to analyze</div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# PAGE 2: ANALYTICS DASHBOARD
# =============================================================================
elif st.session_state.current_page == "dashboard":
    st.markdown("### Operations Analytics Dashboard")
    st.markdown("Aggregated metrics and distribution charts from the platform database.")

    all_reports = database.get_all_reports()
    types = sorted(set(r['incident_type'] for r in all_reports))
    instruments = sorted(set(r['instruments_detected'] for r in all_reports if r['instruments_detected']))

    # Filters in a plain container (no st.container(border) to avoid the circle bug)
    st.markdown("""
    <div style="background-color: #FFFFFF; border: 1px solid #E4E7EC; border-radius: 10px; padding: 16px 20px; margin-bottom: 24px;">
        <div style="font-size: 14px; font-weight: 600; color: #171A1F; margin-bottom: 12px;">Dashboard Filters</div>
    </div>
    """, unsafe_allow_html=True)

    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        sel_types = st.multiselect("Incident Types", options=types, default=types)
    with f_col2:
        sel_inst = st.multiselect("Instruments", options=instruments, default=instruments)
    with f_col3:
        min_sev, max_sev = st.select_slider(
            "Severity Range",
            options=[1, 2, 3, 4, 5],
            value=(1, 5)
        )

    # Apply filters
    filtered_db = [
        r for r in all_reports
        if r['incident_type'] in sel_types
        and (not r['instruments_detected'] or r['instruments_detected'] in sel_inst)
        and (min_sev <= int(r['severity']) <= max_sev)
    ]

    df = pd.DataFrame(filtered_db)

    # Metric cards using st.metric directly (not wrapped in st.container)
    st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

    with m_col1:
        st.metric("Total Logged Incidents", len(filtered_db))
    with m_col2:
        under_review_count = len([r for r in filtered_db if r['verification_status'] == 'Under Review'])
        st.metric("Active Under Review", under_review_count)
    with m_col3:
        critical_count = len([r for r in filtered_db if int(r['severity']) >= 4])
        st.metric("Critical Alerts (Sev 4-5)", critical_count)
    with m_col4:
        avg_conf = df['confidence_score'].mean() if not df.empty else 0.0
        st.metric("Avg Confidence Score", f"{avg_conf:.1f}%")

    if not df.empty:
        st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
        chart_col1, chart_col2 = st.columns(2, gap="large")

        with chart_col1:
            st.markdown("##### Incident Count by Category")
            type_counts = df['incident_type'].value_counts().reset_index()
            type_counts.columns = ['Category', 'Count']
            st.bar_chart(type_counts.set_index('Category'))

        with chart_col2:
            st.markdown("##### Incidents by Severity Level")
            sev_counts = df['severity'].value_counts().reset_index()
            sev_counts.columns = ['Severity Level', 'Count']
            sev_counts = sev_counts.sort_values(by='Severity Level')
            st.bar_chart(sev_counts.set_index('Severity Level'))

        st.markdown("##### Filtered Records Log")
        display_df = df[['id', 'incident_type', 'location', 'start_timestamp', 'end_timestamp', 'severity', 'confidence_score', 'verification_status']].copy()
        display_df.columns = ['ID', 'Incident Type', 'Location', 'Start', 'End', 'Severity', 'Confidence (%)', 'Status']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data matches the selected filters. Please expand your filter options.")
