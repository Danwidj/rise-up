import sys
import os
import time
import contextlib
import tempfile
from pathlib import Path

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

# Set Page Config
st.set_page_config(
    page_title="Nemotron Video Analyzer",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Dark-Themed Glassmorphism UI
st.markdown("""
<style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
        background-color: #0d0f14;
        color: #e2e8f0;
    }
    
    /* Headers styling */
    h1, h2, h3, h4, h5, h6 {
        font-weight: 600;
        background: linear-gradient(135deg, #a7f3d0 0%, #34d399 50%, #059669 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Glassmorphism containers */
    div[data-testid="stVerticalBlock"] > div {
        background-color: rgba(22, 28, 36, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 5px;
        backdrop-filter: blur(10px);
        margin-bottom: 10px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Text inputs */
    input, textarea, select {
        background-color: #1f2937 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #f3f4f6 !important;
        border-radius: 8px !important;
    }
    
    /* Buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        border: none;
        color: #ffffff;
        padding: 10px 24px;
        font-weight: 600;
        border-radius: 8px;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #34d399 0%, #10b981 100%);
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.3);
        transform: translateY(-1px);
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
        # Display the live stdout output in a terminal code block
        self.placeholder.code(self.content, language="text")

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

# Title
st.title("🎥 Nemotron Omni Video Analyzer")
st.markdown("Query the **NVIDIA Nemotron Omni** model with video inputs from Cloudflare R2.")

# --- CHECK CREDENTIALS ---
missing_credentials = []
for var in ["R2_BUCKET", "R2_ACCOUNT_ID", "R2_ACCESS_KEY", "R2_SECRET_KEY"]:
    if not os.getenv(var):
        missing_credentials.append(var)

if missing_credentials:
    st.error(f"⚠️ Missing Cloudflare R2 configuration: {', '.join(missing_credentials)}")
    st.warning("Please configure your `.env` file in the project root with the correct credentials.")
    st.stop()

if not os.getenv("NVIDIA_API_KEY"):
    st.warning("⚠️ Missing `NVIDIA_API_KEY`. You will not be able to perform AI video analysis, but you can still list and stream videos.")

# --- SIDEBAR: Video Selector & Upload ---
with st.sidebar:
    st.header("📂 Video Library")
    
    # 1. Fetch available videos from R2
    try:
        with st.spinner("Fetching library from R2..."):
            all_objects = r2.list_objects()
        videos = [obj for obj in all_objects if obj.lower().endswith(".mp4")]
    except Exception as e:
        st.error(f"Failed to list R2 files: {e}")
        videos = []
    
    # 2. Search Box
    search_query = st.text_input("🔍 Search videos...", "").strip()
    
    # 3. Dynamic Filter
    if search_query:
        filtered_videos = [v for v in videos if search_query.lower() in v.lower()]
    else:
        filtered_videos = videos
        
    # 4. Selection
    if filtered_videos:
        selected_video = st.selectbox(
            f"Select a video ({len(filtered_videos)} found)",
            filtered_videos
        )
    else:
        st.info("No videos found matching your query.")
        selected_video = None
        
    st.markdown("---")
    
    # 5. Upload Widget
    st.header("📤 Upload Video")
    uploaded_file = st.file_uploader("Choose a local .mp4 video file", type=["mp4"])
    if uploaded_file is not None:
        file_name = uploaded_file.name
        st.info(f"Ready to upload: `{file_name}`")
        if st.button("Upload to R2"):
            with st.spinner("Uploading to Cloudflare R2..."):
                try:
                    # Save to local temporary file first
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name
                    
                    r2.upload_file(tmp_path, file_name)
                    st.success(f"Successfully uploaded `{file_name}`!")
                    time.sleep(1)
                    # Force page rerun to refresh the library listing
                    st.rerun()
                except Exception as e:
                    st.error(f"Upload failed: {e}")
                finally:
                    if 'tmp_path' in locals() and os.path.exists(tmp_path):
                        os.unlink(tmp_path)

# --- MAIN CONTENT AREA ---
if selected_video:
    col1, col2 = st.columns([1, 1], gap="medium")
    
    # Left Column: Video Playback
    with col1:
        st.subheader("📺 Video Player")
        try:
            # Generate temporary streaming URL
            video_url = r2.generate_presigned_url(selected_video)
            st.video(video_url)
            st.caption(f"Currently playing: `{selected_video}`")
        except Exception as e:
            st.error(f"Failed to load video streaming URL: {e}")
            
    # Right Column: Controls and Prompts
    with col2:
        st.subheader("⚙️ Analysis Panel")
        
        # Suggested Presets
        prompt_presets = [
            "Describe this video in detail.",
            "Explain what actions or anomalies are happening in this video.",
            "Is there any suspicious behavior or safety concerns (e.g. stealing, shoplifting, vandalism) in this video?",
            "Write a concise summary of the timeline of events in this clip."
        ]
        selected_preset = st.selectbox("📝 Prompt Presets", prompt_presets)
        
        prompt = st.text_area("Customize prompt:", value=selected_preset, height=80)
        
        # Toggles and Parameters
        think = st.toggle("🧠 Enable Reasoning (/think mode)", value=True)
        
        with st.expander("🛠️ Advanced Settings", expanded=False):
            max_tokens = st.slider("Max Output Tokens", 1024, 65536, 65536, step=1024)
            temperature = st.slider("Temperature", 0.0, 1.0, 0.6 if think else 0.2, step=0.1)
            reasoning_budget = st.slider("Reasoning Budget (tokens)", 1024, 32768, 16384, step=1024)
            
        analyze_button = st.button("🚀 Analyze Video")
        
    # Full Width Analysis Stream Output
    if analyze_button:
        if not os.getenv("NVIDIA_API_KEY"):
            st.error("Cannot perform analysis: NVIDIA_API_KEY is not set.")
        else:
            st.markdown("---")
            st.subheader("🖥️ Live Terminal Output")
            
            # Temporary files for video checks and compression
            temp_local_file = Path(f"temp_{Path(selected_video).name}")
            temp_compressed_file = Path(f"temp_compressed_{Path(selected_video).name}")
            
            # Status placeholder
            status_box = st.empty()
            terminal_placeholder = st.empty()
            
            try:
                # 1. Download from R2
                status_box.info("📥 Downloading video from Cloudflare R2...")
                r2.download_file(selected_video, temp_local_file)
                
                # 2. Probe and validate video
                status_box.info("🔍 Probing video constraints...")
                info = video.probe_video(str(temp_local_file))
                problems = video.check_constraints(info)
                
                if problems:
                    st.error("Validation failed:")
                    for prob in problems:
                        st.markdown(f"- {prob}")
                    st.stop()
                
                # 3. Size compression check
                active_video_file = temp_local_file
                if info.size_bytes > 19000000:
                    status_box.warning("⚡ Video exceeds payload size. Compressing video...")
                    video.compress_video(str(temp_local_file), str(temp_compressed_file), info.duration_s)
                    active_video_file = temp_compressed_file
                
                # 4. Generate base64 payload
                status_box.info("🔌 Encoding video payload...")
                video_base64_url = video.to_data_url(str(active_video_file))
                
                # 5. Call Streaming Model and redirect its output
                status_box.success("🤖 Sending payload to NVIDIA Nemotron Omni...")
                
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
                    
                status_box.success("✅ Analysis completed successfully!")
                        
            except Exception as e:
                st.error(f"An error occurred: {e}")
                
            finally:
                # Cleanup temp local video files
                for f in (temp_local_file, temp_compressed_file):
                    if f.exists():
                        try:
                            f.unlink()
                        except Exception as e:
                            pass
else:
    st.info("👈 Select a video from the library sidebar to start analysis.")
