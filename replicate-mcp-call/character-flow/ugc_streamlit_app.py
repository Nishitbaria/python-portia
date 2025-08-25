import streamlit as st
import requests
import json
import time
import threading
import queue
from typing import Dict, Any
import cloudinary
import cloudinary.uploader
import os
import re
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="UGC Pro Studio", 
    page_icon="🎬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure Cloudinary with environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Predefined character URLs
PREDEFINED_CHARACTERS = [
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2PZps4l7vwC1fd4pMXytmhRAYDBUcu3HZNSFo",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2q22n4wMQ9MY3OVAuxjS8dZ04DkcXICptv7Ll",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2FKFMHVtDcfnuGL3wbEeCWSgjrohs1AdYBmRp",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2W5lYjcVc9b4PZyL0KhkgSNCqQzuA2xRfs76F",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2wPrOReDfEB1Ku65aICqL0MmlbczDjp2W47h9",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2OPkTFqCT6b0p92cYIEwxLVH4ay3XtMPFsgDk",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2qFhSZAMQ9MY3OVAuxjS8dZ04DkcXICptv7Ll",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2wMnYa8DfEB1Ku65aICqL0MmlbczDjp2W47h9",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2KUEdHyYhTCsONcWmwFvkrLVfYU43P5AoGMEj",
]

# Enhanced Custom CSS for Professional Look
st.markdown(
    """
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .main-header {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 3rem;
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 2rem;
        padding: 1rem 0;
    }
    
    /* Ensure text is visible in dark mode */
    @media (prefers-color-scheme: dark) {
        .step-title, .sub-header, .option-card h3, .option-card p, .option-card li {
            color: #ffffff !important;
        }
        .option-card {
            background: #2d3748 !important;
            border-color: #4a5568 !important;
        }
    }
    
    .sub-header {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        color: #2d3748 !important;
        text-align: center;
        margin-bottom: 3rem;
        font-size: 1.2rem;
    }
    
    /* Step Progress Enhancement */
    .step-container {
        background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 4px solid #667eea;
        margin: 2rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    
    .step-title {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: #e2e8f0 !important;
        font-size: 1.4rem;
        margin-bottom: 1rem;
        text-shadow: none;
    }
    
    /* Card Styles */
    .option-card {
        background: white !important;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #e2e8f0;
        margin: 1rem 0;
        transition: all 0.3s ease;
        cursor: pointer;
        color: #1a202c !important;
    }
    
    .option-card h3 {
        color: #1a202c !important;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .option-card p {
        color: #4a5568 !important;
        margin-bottom: 1rem;
    }
    
    .option-card li {
        color: #4a5568 !important;
        margin: 0.5rem 0;
    }
    
    .option-card:hover {
        border-color: #667eea;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.15);
        transform: translateY(-2px);
    }
    
    .option-card.selected {
        border-color: #667eea;
        background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2);
    }
    
    /* Character Grid Enhancement */
    .character-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .character-card {
        background: white;
        border-radius: 15px;
        padding: 1rem;
        border: 2px solid #e2e8f0;
        transition: all 0.3s ease;
        text-align: center;
        cursor: pointer;
    }
    
    .character-card:hover {
        border-color: #667eea;
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
    }
    
    .character-card.selected {
        border-color: #667eea;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Status Containers */
    .status-container {
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        border-left: 4px solid;
    }
    
    .status-running {
        background: linear-gradient(135deg, #fff3cd 0%, #fef7e0 100%);
        border-left-color: #f59e0b;
        color: #92400e;
    }
    
    .status-completed {
        background: linear-gradient(135deg, #d1fae5 0%, #ecfdf5 100%);
        border-left-color: #10b981;
        color: #065f46;
    }
    
    .status-error {
        background: linear-gradient(135deg, #fee2e2 0%, #fef2f2 100%);
        border-left-color: #ef4444;
        color: #991b1b;
    }
    
    /* Progress Bar Enhancement */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    /* Button Enhancements */
    .stButton > button {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        border-radius: 8px;
        border: none;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
    }
    
    /* Radio Button Enhancement */
    .stRadio > div {
        gap: 1rem;
    }
    
    .stRadio > div > label {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important;
        padding: 1rem;
        color: #1a202c !important;
        border-radius: 10px;
        border: 2px solid #cbd5e0;
        cursor: pointer;
        transition: all 0.3s ease;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .stRadio > div > label > div {
        color: #1a202c !important;
    }
    
    .stRadio > div > label span {
        color: #1a202c !important;
    }
    
    .stRadio > div > label:hover {
        border-color: #667eea;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: #ffffff !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    .stRadio > div > label:hover > div {
        color: #ffffff !important;
    }
    
    .stRadio > div > label:hover span {
        color: #ffffff !important;
    }
    
    /* Selected radio button styling */
    .stRadio > div > label[data-checked="true"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        border-color: #10b981;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }
    
    .stRadio > div > label[data-checked="true"] > div {
        color: #ffffff !important;
    }
    
    .stRadio > div > label[data-checked="true"] span {
        color: #ffffff !important;
    }
    
    /* Sidebar Enhancement */
    .css-1d391kg {
        background: linear-gradient(180deg, #f7fafc 0%, #edf2f7 100%);
    }
    
    /* Testing Button */
    .testing-button {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        font-size: 1.1rem;
        cursor: pointer;
        transition: all 0.3s ease;
        margin: 1rem 0;
    }
    
    .testing-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(255, 107, 107, 0.3);
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Force text visibility */
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        color: inherit !important;
    }
    
    /* Dark theme overrides */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Ensure step container text is visible */
    .step-container p, .step-container div {
        color: #1a202c !important;
    }
    
    /* Fix radio button text visibility */
    .stRadio label {
        color: #f7fafc !important;
    }
    
    .stRadio div[data-testid="stRadio"] > div > label > div {
        color: #1a202c !important;
    }
    
    /* Ensure all radio button text is visible */
    div[data-testid="stRadio"] label {
        color: #f7fafc !important;
    }
    
    div[data-testid="stRadio"] label > div {
        color: #1a202c !important;
    }
    
    /* Radio button question text */
    .stRadio > label {
        color: #f7fafc !important;
        font-weight: 500;
    }
    
    /* All radio group labels */
    div[role="radiogroup"] > label {
        color: #f7fafc !important;
    }
    
    /* Radio button question text - multiple selectors */
    .stRadio > div:first-child {
        color: #f7fafc !important;
    }
    
    div[data-testid="stRadio"] > div:first-child {
        color: #f7fafc !important;
    }
    
    div[data-testid="stRadio"] > div > div:first-child {
        color: #f7fafc !important;
    }
    
    /* Target the legend element which contains the question */
    .stRadio legend {
        color: #f7fafc !important;
    }
    
    div[data-testid="stRadio"] legend {
        color: #f7fafc !important;
    }
    
    /* Target any paragraph within radio group */
    div[data-testid="stRadio"] p {
        color: #f7fafc !important;
    }
    
    /* Force radio button background override */
    div[data-testid="stRadio"] > div > label {
        background: linear-gradient(135deg, #667eea 0%, #667eea 100%) !important;
        border: 2px solid #cbd5e0 !important;
    }
    
    div[data-testid="stRadio"] > div > label:hover {
        background: linear-gradient(135deg, #667eea 0%, #667eea 100%) !important;
        border-color: #667eea !important;
        color: #ffffff !important;
    }
    
    div[data-testid="stRadio"] > div > label:hover > div {
        color: #ffffff !important;
    }
    
    div[data-testid="stRadio"] > div > label:hover span {
        color: #ffffff !important;
    }
    
    /* Selected state using aria-checked */
    div[data-testid="stRadio"] > div > label[aria-checked="true"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        border-color: #10b981 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
    }
    
    div[data-testid="stRadio"] > div > label[aria-checked="true"] > div {
        color: #ffffff !important;
    }
    
    div[data-testid="stRadio"] > div > label[aria-checked="true"] span {
        color: #ffffff !important;
    }
    
    /* Alternative selector for selected state */
    div[data-testid="stRadio"] input[type="radio"]:checked + label {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        border-color: #10b981 !important;
        color: #ffffff !important;
    }
    
    /* Force override any white backgrounds */
    div[data-testid="stRadio"] * {
        background-color: transparent !important;
    }
    
    div[data-testid="stRadio"] > div > label * {
        background-color: transparent !important;
    }
    
    /* Content Spacing */
    .block-container {
        padding: 2rem 3rem;
        max-width: 1200px;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Initialize session state
def init_session_state():
    if "flow_data" not in st.session_state:
        st.session_state.flow_data = {}
    if "current_step" not in st.session_state:
        st.session_state.current_step = "ad_type_selection"
    if "ad_type_choice" not in st.session_state:
        st.session_state.ad_type_choice = None
    if "flow_completed" not in st.session_state:
        st.session_state.flow_completed = False
    if "execution_status" not in st.session_state:
        st.session_state.execution_status = "idle"  # idle, running, completed, error
    if "streaming_events" not in st.session_state:
        st.session_state.streaming_events = []
    if "final_video_url" not in st.session_state:
        st.session_state.final_video_url = None
    if "prediction_id" not in st.session_state:
        st.session_state.prediction_id = None
    if "progress" not in st.session_state:
        st.session_state.progress = 0.0
    if "current_step_name" not in st.session_state:
        st.session_state.current_step_name = "Not started"
    if "show_social_sharing" not in st.session_state:
        st.session_state.show_social_sharing = False
    if "social_sharing_data" not in st.session_state:
        st.session_state.social_sharing_data = {}
    if "social_plan_run_id" not in st.session_state:
        st.session_state.social_plan_run_id = None
    if "generated_product_description" not in st.session_state:
        st.session_state.generated_product_description = ""
    if "generated_dialog" not in st.session_state:
        st.session_state.generated_dialog = ""


init_session_state()


# Helper functions
def validate_url(url):
    """Validate URL format"""
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\\.)+)"  # domain...
        r"(?:[A-Z]{2,6}\\.?|[A-Z0-9-]{2,}\\.?)|"  # host...
        r"localhost|"  # localhost...
        r"\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})"  # ...or ip
        r"(?::\\d+)?"  # optional port
        r"(?:/?|[/?]\\S+)$",
        re.IGNORECASE,
    )
    return url_pattern.match(url) is not None


def upload_to_cloudinary(uploaded_file):
    """Upload file to Cloudinary and return URL"""
    try:
        # Check if Cloudinary is configured
        if not all(
            [
                os.getenv("CLOUDINARY_CLOUD_NAME"),
                os.getenv("CLOUDINARY_API_KEY"),
                os.getenv("CLOUDINARY_API_SECRET"),
            ]
        ):
            st.error(
                "❌ Cloudinary credentials not configured. Please check your .env file."
            )
            return None

        # Convert uploaded file to bytes
        bytes_data = uploaded_file.read()

        # Upload to Cloudinary
        with st.spinner("Uploading image..."):
            upload_result = cloudinary.uploader.upload(
                bytes_data,
                resource_type="image",
                unique_filename=True,
                overwrite=True,
            )

        # Get the secure URL
        image_url = upload_result.get("secure_url")

        if image_url:
            st.success(f"✅ Image uploaded successfully!")
            return image_url
        else:
            st.error("❌ Failed to get image URL from Cloudinary")
            return None

    except Exception as e:
        st.error(f"❌ Error uploading image: {str(e)}")
        return None


def reset_flow():
    """Reset the entire flow"""
    st.session_state.flow_data = {}
    st.session_state.current_step = "ad_type_selection"
    st.session_state.ad_type_choice = None
    st.session_state.flow_completed = False
    st.session_state.execution_status = "idle"
    st.session_state.streaming_events = []
    st.session_state.final_video_url = None
    st.session_state.prediction_id = None
    st.session_state.progress = 0.0
    st.session_state.current_step_name = "Not started"
    st.session_state.show_social_sharing = False
    st.session_state.social_sharing_data = {}
    st.session_state.social_plan_run_id = None
    st.session_state.generated_product_description = ""
    st.session_state.generated_dialog = ""
    # Clean up character selection state
    if "selected_character_index" in st.session_state:
        del st.session_state.selected_character_index


def check_api_health():
    """Check if the API server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def parse_sse_line(line: str) -> Dict[str, Any]:
    """Parse a single SSE line"""
    if line.startswith("data: "):
        try:
            return json.loads(line[6:])  # Remove "data: " prefix
        except json.JSONDecodeError:
            return {"type": "error", "message": f"Invalid JSON: {line}"}
    return None

def parse_sse_chunk(chunk: str) -> list:
    """Parse SSE chunk that might contain multiple events"""
    events = []
    lines = chunk.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith("data: "):
            try:
                event_data = json.loads(line[6:])  # Remove "data: " prefix
                events.append(event_data)
            except json.JSONDecodeError:
                events.append({"type": "error", "message": f"Invalid JSON: {line}"})
    
    return events


def stream_ugc_execution_realtime(payload: Dict[str, Any], status_placeholder, progress_placeholder, events_placeholder):
    """Stream UGC execution with real-time UI updates using placeholders"""
    try:
        # Make streaming request
        response = requests.post(
            f"{API_BASE_URL}/execute-ugc-realtime",
            json=payload,
            stream=True,
            timeout=1200,  # 10 minute timeout
        )

        response.raise_for_status()

        step_counter = 0
        total_steps = 12  # Approximate based on UGC generator plan

        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                event = parse_sse_line(line_str)

                if event:
                    # Add to events list
                    event_with_time = {**event, "timestamp": time.strftime("%H:%M:%S")}
                    st.session_state.streaming_events.append(event_with_time)

                    # Update progress based on event type
                    if event["type"] == "started":
                        st.session_state.current_step_name = "Initializing..."
                        st.session_state.progress = 0.05

                    elif event["type"] == "step_started":
                        step_name = event.get("step_name", "Unknown step")
                        st.session_state.current_step_name = f"Starting: {step_name}"

                    elif event["type"] == "step_completed":
                        step_counter += 1
                        step_name = event.get("step_name", "Unknown step")
                        output = event.get("output", "")
                        
                        # Extract product description and dialog for social sharing
                        if "product_description" in step_name.lower() and output:
                            st.session_state.generated_product_description = output
                        elif "dialog" in step_name.lower() and output:
                            st.session_state.generated_dialog = output
                        
                        st.session_state.current_step_name = f"Completed: {step_name}"
                        st.session_state.progress = min(
                            step_counter / total_steps * 0.8, 0.8
                        )  # Max 80% until video completion

                    elif event["type"] == "plan_completed":
                        st.session_state.current_step_name = (
                            "Plan completed - generating video..."
                        )
                        st.session_state.progress = 0.85
                        if event.get("prediction_id"):
                            st.session_state.prediction_id = event["prediction_id"]

                    elif event["type"] == "video_polling_started":
                        st.session_state.current_step_name = (
                            "Polling for video completion..."
                        )
                        st.session_state.progress = 0.9

                    elif event["type"] == "video_completed":
                        video_url = event.get("video_url")
                        if video_url:
                            st.session_state.final_video_url = video_url
                        st.session_state.current_step_name = (
                            "✅ Video generation completed!"
                        )
                        st.session_state.progress = 1.0
                        st.session_state.execution_status = "completed"
                        
                        # Enable social sharing option
                        st.session_state.show_social_sharing = True
                        
                        # Update UI immediately
                        update_realtime_display(status_placeholder, progress_placeholder, events_placeholder)
                        break

                    elif event["type"] == "video_failed":
                        st.session_state.current_step_name = f"❌ Video generation failed: {event.get('message', 'Unknown error')}"
                        st.session_state.execution_status = "error"
                        update_realtime_display(status_placeholder, progress_placeholder, events_placeholder)
                        break

                    elif event["type"] == "error":
                        st.session_state.current_step_name = (
                            f"❌ Error: {event.get('message', 'Unknown error')}"
                        )
                        st.session_state.execution_status = "error"
                        update_realtime_display(status_placeholder, progress_placeholder, events_placeholder)
                        break

                    # Update display for each event
                    update_realtime_display(status_placeholder, progress_placeholder, events_placeholder)

        # Mark as completed if no error occurred and not already set
        if st.session_state.execution_status == "running":
            st.session_state.execution_status = "completed"
            st.session_state.current_step_name = "✅ Execution completed!"
            update_realtime_display(status_placeholder, progress_placeholder, events_placeholder)

    except requests.exceptions.RequestException as e:
        st.session_state.streaming_events.append(
            {
                "type": "error",
                "message": f"API request failed: {str(e)}",
                "timestamp": time.strftime("%H:%M:%S"),
            }
        )
        st.session_state.execution_status = "error"
        st.session_state.current_step_name = f"❌ Connection error: {str(e)}"
        update_realtime_display(status_placeholder, progress_placeholder, events_placeholder)
    except Exception as e:
        st.session_state.streaming_events.append(
            {
                "type": "error",
                "message": f"Streaming error: {str(e)}",
                "timestamp": time.strftime("%H:%M:%S"),
            }
        )
        st.session_state.execution_status = "error"
        st.session_state.current_step_name = f"❌ Streaming error: {str(e)}"
        update_realtime_display(status_placeholder, progress_placeholder, events_placeholder)


def update_realtime_display(status_placeholder, progress_placeholder, events_placeholder):
    """Update the real-time display elements"""
    # Update progress
    with progress_placeholder.container():
        st.progress(st.session_state.progress)
    
    # Update status
    with status_placeholder.container():
        st.write(f"**Current Status:** {st.session_state.current_step_name}")
    
    # Update events log
    if st.session_state.streaming_events:
        with events_placeholder.container():
            st.markdown("### 🔍 Live Events Log")
            # Show last 5 events
            recent_events = st.session_state.streaming_events[-5:]
            for event in reversed(recent_events):
                event_type = event.get("type", "unknown")
                event_message = event.get("message", str(event))
                event_time = event.get("timestamp", "")

                if event_type == "error":
                    st.error(f"[{event_time}] ❌ {event_message}")
                elif event_type in [
                    "step_completed",
                    "video_completed", 
                    "plan_completed",
                ]:
                    st.success(f"[{event_time}] ✅ {event_message}")
                elif event_type in ["step_started", "video_polling_started"]:
                    st.info(f"[{event_time}] ⏳ {event_message}")
                else:
                    st.write(f"[{event_time}] 📍 {event_type}: {event_message}")


def stream_product_ad_execution(payload: Dict[str, Any], status_placeholder, progress_placeholder, events_placeholder):
    """Stream Product Ad execution with real-time UI updates"""
    try:
        # Make request to Product Ad API
        response = requests.post(
            f"{API_BASE_URL}/execute-product-ad",
            json=payload,
            timeout=1200,  # 10 minute timeout
        )

        response.raise_for_status()
        result = response.json()

        # Handle the result
        if result.get("status") == "completed":
            video_url = result.get("video_url")
            st.session_state.final_video_url = video_url
            st.session_state.current_step_name = "✅ Product Ad generation completed!"
            st.session_state.progress = 1.0
            st.session_state.execution_status = "completed"
            
            # Add event to log
            st.session_state.streaming_events.append({
                "type": "video_completed",
                "video_url": video_url,
                "message": "Product Ad generation completed!",
                "timestamp": time.strftime("%H:%M:%S")
            })
            
        elif result.get("status") == "failed":
            error_message = result.get("error", "Unknown error")
            st.session_state.current_step_name = f"❌ Product Ad generation failed: {error_message}"
            st.session_state.execution_status = "error"
            
            # Add error to log
            st.session_state.streaming_events.append({
                "type": "error",
                "message": f"Product Ad generation failed: {error_message}",
                "timestamp": time.strftime("%H:%M:%S")
            })
        
        # Update display
        update_realtime_display(status_placeholder, progress_placeholder, events_placeholder)

    except requests.exceptions.RequestException as e:
        st.session_state.streaming_events.append({
            "type": "error",
            "message": f"API request failed: {str(e)}",
            "timestamp": time.strftime("%H:%M:%S"),
        })
        st.session_state.execution_status = "error"
        st.session_state.current_step_name = f"❌ Connection error: {str(e)}"
        update_realtime_display(status_placeholder, progress_placeholder, events_placeholder)
    except Exception as e:
        st.session_state.streaming_events.append({
            "type": "error",
            "message": f"Product Ad error: {str(e)}",
            "timestamp": time.strftime("%H:%M:%S"),
        })
        st.session_state.execution_status = "error"
        st.session_state.current_step_name = f"❌ Product Ad error: {str(e)}"
        update_realtime_display(status_placeholder, progress_placeholder, events_placeholder)


def stream_ugc_execution(payload: Dict[str, Any]):
    """Legacy function - kept for compatibility"""
    # This is the old function that used threading - now we use the real-time version
    pass


# Main title with subtitle
st.markdown(
    '''
    <div class="main-header">🎬 UGC Pro Studio</div>
    <div class="sub-header">Create stunning UGC ads and social media content with AI</div>
    ''',
    unsafe_allow_html=True,
)

# API Status check - only check once per session
if "api_status_checked" not in st.session_state:
    st.session_state.api_status_checked = check_api_health()

if not st.session_state.api_status_checked:
    st.error(
        "❌ API Server is not running! Please start the API server at http://localhost:8000"
    )
    st.info("Run: `python api_server.py` to start the server")
    if st.button("🔄 Retry Connection"):
        st.session_state.api_status_checked = check_api_health()
        st.rerun()
    st.stop()
else:
    st.success("✅ API Server is running")

# 🚀 TESTING SHORTCUT - Add a quick test button
st.markdown("---")
if st.button("🧪 **TESTING: Jump to Social Media Sharing**", type="primary"):
    # Set up hardcoded values for testing
    st.session_state.ad_type_choice = "1"  # UGC Ad
    st.session_state.current_step = "social_sharing"
    st.session_state.execution_status = "idle"
    st.session_state.final_video_url = "https://replicate.delivery/pbxt/abc123/output.mp4"  # Fake video URL for testing
    st.session_state.generated_product_description = "Amazing UGC Video Product - showcases the best features"
    st.session_state.generated_dialog = "Check out this amazing product! It's absolutely fantastic and I love using it every day."
    st.session_state.show_social_sharing = True
    st.rerun()

st.markdown("---")

# Show progress
if st.session_state.ad_type_choice == "1":  # UGC Ad
    steps = [
        "Ad Type Selection",
        "Character Selection",
        "Product Image", 
        "Dialog Generation",
        "Execute & Monitor",
        "Social Sharing",
    ]
    current_step_index = {
        "ad_type_selection": 0,
        "character_selection": 1,
        "product_image": 2,
        "dialog_generation": 3,
        "execution": 4,
        "social_sharing": 5,
    }.get(st.session_state.current_step, 0)
elif st.session_state.ad_type_choice == "2":  # Product Ad
    steps = [
        "Ad Type Selection",
        "Product Image",
        "Ad Prompt",
        "Execute & Monitor",
    ]
    current_step_index = {
        "ad_type_selection": 0,
        "product_image": 1,
        "ad_prompt": 2,
        "execution": 3,
    }.get(st.session_state.current_step, 0)
else:  # No choice made yet
    steps = ["Ad Type Selection"]
    current_step_index = 0

st.progress((current_step_index + 1) / len(steps))
st.write(
    f"**Step {current_step_index + 1} of {len(steps)}: {steps[current_step_index]}**"
)

# Step 0: Ad Type Selection
if st.session_state.current_step == "ad_type_selection":
    st.markdown('<div class="step-title">Choose Your Ad Type</div>', unsafe_allow_html=True)
    st.markdown('<p style="color: #4a5568 !important; font-size: 1.1rem; margin-bottom: 2rem;">Select the type of advertisement you\'d like to create</p>', unsafe_allow_html=True)
    
    # Create two columns for ad type cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            '''
            <div class="option-card">
                <h3>🎬 UGC Advertisement</h3>
                <p>Create personalized video content with virtual characters and custom dialog</p>
                <ul>
                    <li>✨ Character-driven content</li>
                    <li>🗣️ Custom or auto-generated dialog</li>
                    <li>📱 Perfect for social media</li>
                </ul>
            </div>
            ''', 
            unsafe_allow_html=True
        )
        if st.button("Create UGC Ad", key="ugc_btn", type="primary", use_container_width=True):
            st.session_state.ad_type_choice = "1"
            st.session_state.current_step = "character_selection"
            st.rerun()
    
    with col2:
        st.markdown(
            '''
            <div class="option-card">
                <h3>📸 Product Advertisement</h3>
                <p>Generate focused product videos with custom prompts and professional styling</p>
                <ul>
                    <li>🎯 Product-focused content</li>
                    <li>✍️ Custom prompts</li>
                    <li>🎨 Professional presentation</li>
                </ul>
            </div>
            ''', 
            unsafe_allow_html=True
        )
        if st.button("Create Product Ad", key="product_btn", type="primary", use_container_width=True):
            st.session_state.ad_type_choice = "2"
            st.session_state.current_step = "product_image"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Step 1: Character Selection (UGC only)
elif st.session_state.current_step == "character_selection":
    st.markdown('<div class="step-title">🎭 Choose Your Character</div>', unsafe_allow_html=True)
    st.markdown("Select how you'd like to provide the character for your UGC ad", unsafe_allow_html=True)

    character_choice = st.radio(
        "Character Options:",
        ["🆕 Bring your own character", "🎭 Use our prebuild characters"],
        key="character_choice_radio",
    )

    if character_choice == "🆕 Bring your own character":
        st.write("🆕 You chose to bring your own character")
        character_url = st.text_input(
            "Enter the URL of your character:",
            key="custom_character_url",
            placeholder="https://example.com/character.jpg",
        )

        if character_url:
            if validate_url(character_url):
                if st.button("Confirm Character URL", type="primary"):
                    st.session_state.flow_data["character_choice"] = "1"
                    st.session_state.flow_data["custom_character_url"] = character_url
                    st.session_state.current_step = "product_image"
                    st.rerun()
            else:
                st.error(
                    "❌ Please enter a valid URL (must start with http:// or https://)"
                )

    elif character_choice == "🎭 Use our prebuild characters":
        st.markdown("### Gallery of Available Characters")
        st.markdown("Choose from our curated collection of professional characters")

        # Initialize selected character if not exists
        if "selected_character_index" not in st.session_state:
            st.session_state.selected_character_index = None

        # Display character options in a responsive grid
        cols = st.columns(3)

        for i, url in enumerate(PREDEFINED_CHARACTERS):
            col_index = i % 3
            with cols[col_index]:
                # Check if this character is currently selected
                is_selected = st.session_state.selected_character_index == i
                
                # Create character card
                card_class = "character-card selected" if is_selected else "character-card"
                
                # st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
                
                try:
                    st.image(url, width=150)
                except:
                    st.markdown("**Character Preview**")
                    st.markdown("*Image loading...*")
                
                st.markdown(f"**Character {i+1}**")
                
                # Selection button
                button_type = "primary" if is_selected else "secondary"
                button_label = "✅ Selected" if is_selected else f"Select"

                if st.button(
                    button_label,
                    key=f"select_char_{i}",
                    type=button_type,
                    use_container_width=True,
                ):
                    if not is_selected:
                        st.session_state.selected_character_index = i
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

        # Confirmation section
        if st.session_state.selected_character_index is not None:
            selected_index = st.session_state.selected_character_index
            st.markdown("---")
            st.success(f"✅ Character {selected_index + 1} selected")
            
            col1, col2 = st.columns([1, 1])
            with col2:
                if st.button("Continue with Selected Character", type="primary", use_container_width=True):
                    st.session_state.flow_data["character_choice"] = "2"
                    st.session_state.flow_data["prebuild_character_choice"] = selected_index + 1
                    st.session_state.flow_data["character_url"] = PREDEFINED_CHARACTERS[selected_index]
                    st.session_state.current_step = "product_image"
                    if "selected_character_index" in st.session_state:
                        del st.session_state.selected_character_index
                    st.rerun()
        
        # Back button
        if st.button("← Back to Ad Type Selection"):
            st.session_state.current_step = "ad_type_selection"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Step 2: Product Image
elif st.session_state.current_step == "product_image":
    st.markdown('<div class="step-title">📸 Product Image</div>', unsafe_allow_html=True)
    st.markdown("Provide your product image to create stunning advertisement content")

    product_option = st.radio(
        "How would you like to provide your product image?",
        ["📁 Upload file here", "🔗 Enter URL directly"],
        key="product_option_radio",
    )

    if product_option == "📁 Upload file here":
        uploaded_file = st.file_uploader(
            "Choose a product image...",
            type=["png", "jpg", "jpeg", "gif", "bmp", "webp"],
            key="product_file_upload",
        )

        if uploaded_file:
            st.image(uploaded_file, caption="Product Image Preview", width=300)

            if st.button("Upload Image", type="primary"):
                product_url = upload_to_cloudinary(uploaded_file)
                if product_url:
                    st.session_state.flow_data["product_image_source"] = "upload"
                    st.session_state.flow_data["product_url"] = product_url
                    # Next step depends on ad type
                    if st.session_state.ad_type_choice == "1":  # UGC Ad
                        st.session_state.current_step = "dialog_generation"
                    else:  # Product Ad
                        st.session_state.current_step = "ad_prompt"
                    st.rerun()

    else:  # Enter URL directly
        product_url = st.text_input(
            "Enter the product image URL:",
            key="product_url_input",
            placeholder="https://example.com/product.jpg",
        )

        if product_url:
            if validate_url(product_url):
                st.image(product_url, caption="Product Image Preview", width=300)

                if st.button("Confirm Product URL", type="primary"):
                    st.session_state.flow_data["product_image_source"] = "url"
                    st.session_state.flow_data["product_url"] = product_url
                    # Next step depends on ad type
                    if st.session_state.ad_type_choice == "1":  # UGC Ad
                        st.session_state.current_step = "dialog_generation"
                    else:  # Product Ad
                        st.session_state.current_step = "ad_prompt"
                    st.rerun()
            else:
                st.error(
                    "❌ Please enter a valid URL (must start with http:// or https://)"
                )

    # Back button - depends on ad type
    if st.session_state.ad_type_choice == "1":  # UGC Ad
        if st.button("← Back to Character Selection"):
            st.session_state.current_step = "character_selection"
            st.rerun()
    else:  # Product Ad
        if st.button("← Back to Ad Type Selection"):
            st.session_state.current_step = "ad_type_selection"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Step 3: Dialog Generation
elif st.session_state.current_step == "dialog_generation":
    st.markdown('<div class="step-title">💬 Dialog Generation</div>', unsafe_allow_html=True)
    st.markdown("Create engaging dialog for your character-driven UGC content")

    dialog_choice = st.radio(
        "How would you like to create the dialog?",
        ["✍️ Enter custom dialog", "🤖 Auto generate dialog"],
        index=1,  # Auto-select "Auto generate dialog" (index 1)
        key="dialog_choice_radio",
    )

    if dialog_choice == "✍️ Enter custom dialog":
        st.markdown("### ✍️ Custom Dialog")
        st.markdown("Write your own personalized dialog for the character")
        custom_dialog = st.text_area(
            "Enter your custom dialog:",
            key="custom_dialog_input",
            placeholder="Enter your dialog here...",
            height=150,
        )

        if custom_dialog.strip():
            if st.button("Confirm Custom Dialog", type="primary"):
                st.session_state.flow_data["dialog_choice"] = "1"
                st.session_state.flow_data["custom_dialog"] = custom_dialog.strip()
                st.session_state.current_step = "execution"
                st.session_state.flow_completed = True
                st.rerun()
        else:
            st.warning("⚠️ Please enter some dialog content")

    elif dialog_choice == "🤖 Auto generate dialog":
        st.markdown("### 🤖 AI-Generated Dialog")
        st.markdown("Our AI will create engaging, natural-sounding dialog based on your product")
        st.info("💡 The AI will analyze your product and create contextually relevant dialog that feels authentic and engaging.")

        if st.button("Continue with AI Dialog", type="primary", use_container_width=True):
            st.session_state.flow_data["dialog_choice"] = "2"
            st.session_state.current_step = "execution"
            st.session_state.flow_completed = True
            st.rerun()

    if st.button("← Back to Product Image"):
        st.session_state.current_step = "product_image"
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Step 3.5: Ad Prompt (Product Ad only)
elif st.session_state.current_step == "ad_prompt":
    st.markdown('<div class="step-title">✨ Ad Prompt Creation</div>', unsafe_allow_html=True)
    st.markdown("Create a compelling prompt to generate your product advertisement")
    
    st.markdown(
        '''
        <div style="background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); 
                    padding: 1.5rem; border-radius: 12px; margin: 1.5rem 0;
                    border-left: 4px solid #667eea;">
            <h4 style="color: #2d3748; margin-bottom: 1rem;">💡 Prompt Guidelines</h4>
            <p style="margin: 0.5rem 0;">• Describe the video style and mood</p>
            <p style="margin: 0.5rem 0;">• Mention key features to highlight</p>
            <p style="margin: 0.5rem 0;">• Specify camera angles or movements</p>
            <p style="margin: 0.5rem 0;">• Include lighting or atmosphere preferences</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    ad_prompt = st.text_area(
        "🎯 Enter your ad prompt:",
        key="ad_prompt_input",
        placeholder="Example: Create a dynamic product showcase highlighting the key features of this item with professional lighting and smooth camera movements",
        height=150,
    )
    
    if ad_prompt.strip():
        if st.button("🚀 Create Product Ad", type="primary", use_container_width=True):
            st.session_state.flow_data["ad_prompt"] = ad_prompt.strip()
            st.session_state.current_step = "execution"
            st.session_state.flow_completed = True
            st.rerun()
    else:
        st.warning("⚠️ Please enter an ad prompt to continue")
    
    if st.button("← Back to Product Image"):
        st.session_state.current_step = "product_image"
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Step 4: Execution & Monitoring
elif st.session_state.current_step == "execution":
    if st.session_state.ad_type_choice == "1":
        st.markdown('<div class="step-title">🚀 UGC Ad Generation & Live Monitoring</div>', unsafe_allow_html=True)
        st.markdown("Watch your UGC advertisement come to life in real-time")
    else:
        st.markdown('<div class="step-title">🚀 Product Ad Generation & Live Monitoring</div>', unsafe_allow_html=True)
        st.markdown("Creating your professional product advertisement with AI")

    # Display collected input summary
    with st.expander("📋 Input Summary", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            if st.session_state.ad_type_choice == "1":  # UGC Ad
                st.write("**🎭 Character:**")
                if st.session_state.flow_data.get("character_choice") == "1":
                    st.write(f"- Type: Custom character")
                    st.write(
                        f"- URL: {st.session_state.flow_data.get('custom_character_url')}"
                    )
                else:
                    st.write(
                        f"- Type: Prebuild character #{st.session_state.flow_data.get('prebuild_character_choice')}"
                    )
                    st.write(f"- URL: {st.session_state.flow_data.get('character_url')}")

                st.write("**💬 Dialog:**")
                if st.session_state.flow_data.get("dialog_choice") == "1":
                    st.write(f"- Type: Custom dialog")
                    st.write(
                        f"- Content: {st.session_state.flow_data.get('custom_dialog', '')[:100]}..."
                    )
                else:
                    st.write("- Type: Auto-generated")
            else:  # Product Ad
                st.write("**📸 Ad Type:**")
                st.write("- Type: Product Ad")
                
                st.write("**✨ Ad Prompt:**")
                st.write(f"- Content: {st.session_state.flow_data.get('ad_prompt', '')[:100]}...")

        with col2:
            st.write("**📦 Product:**")
            st.write(
                f"- Source: {st.session_state.flow_data.get('product_image_source', 'URL')}"
            )
            st.write(f"- URL: {st.session_state.flow_data.get('product_url', '')}")

    # Real-time execution status
    if st.session_state.execution_status == "idle":
        st.markdown(
            '''
            <div class="status-container" style="background: linear-gradient(135deg, #e6f3ff 0%, #f0f9ff 100%);
                                              border-left-color: #3b82f6; color: #1e40af;">
                <h3 style="margin: 0; color: #1e40af;">🎯 Ready to Execute</h3>
                <p style="margin: 0.5rem 0 0 0; color: #3b82f6;">All parameters configured. Click below to start generation.</p>
            </div>
            ''',
            unsafe_allow_html=True
        )

        button_text = "🚀 Start UGC Generation" if st.session_state.ad_type_choice == "1" else "🚀 Start Product Ad Generation"
        if st.button(button_text, type="primary", use_container_width=True):
            # Prepare API payload based on ad type
            if st.session_state.ad_type_choice == "1":  # UGC Ad
                api_payload = {
                    "character_choice": st.session_state.flow_data["character_choice"],
                    "product_url": st.session_state.flow_data["product_url"],
                    "dialog_choice": st.session_state.flow_data["dialog_choice"],
                }

                # Add conditional fields
                if st.session_state.flow_data["character_choice"] == "1":
                    api_payload["custom_character_url"] = st.session_state.flow_data[
                        "custom_character_url"
                    ]
                else:
                    api_payload["prebuild_character_choice"] = st.session_state.flow_data[
                        "prebuild_character_choice"
                    ]

                if st.session_state.flow_data["dialog_choice"] == "1":
                    api_payload["custom_dialog"] = st.session_state.flow_data[
                        "custom_dialog"
                    ]
            else:  # Product Ad
                api_payload = {
                    "product_url": st.session_state.flow_data["product_url"],
                    "ad_prompt": st.session_state.flow_data["ad_prompt"],
                }

            # Set execution status and clear previous events
            st.session_state.execution_status = "running"
            st.session_state.streaming_events = []
            st.session_state.final_video_url = None
            st.session_state.progress = 0.0
            st.session_state.current_step_name = "Starting..."

            # Start streaming with real-time updates using direct execution
            st.rerun()

    elif st.session_state.execution_status == "running":
        st.markdown(
            '''
            <div class="status-running">
                <h3 style="margin: 0; color: #92400e;">🔄 Execution in Progress</h3>
                <p style="margin: 0.5rem 0 0 0; color: #92400e;">Generating your content with AI. This may take a few minutes.</p>
            </div>
            ''',
            unsafe_allow_html=True
        )

        # Create placeholders for real-time updates
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        events_placeholder = st.empty()

        # Initialize display
        with progress_placeholder.container():
            st.progress(st.session_state.progress)
        
        with status_placeholder.container():
            st.write(f"**Current Status:** {st.session_state.current_step_name}")

        # If this is the first time in running state, start the streaming
        if not hasattr(st.session_state, 'streaming_started') or not st.session_state.streaming_started:
            st.session_state.streaming_started = True
            
            # Prepare API payload from stored data based on ad type
            if st.session_state.ad_type_choice == "1":  # UGC Ad
                api_payload = {
                    "character_choice": st.session_state.flow_data["character_choice"],
                    "product_url": st.session_state.flow_data["product_url"],
                    "dialog_choice": st.session_state.flow_data["dialog_choice"],
                }

                # Add conditional fields
                if st.session_state.flow_data["character_choice"] == "1":
                    api_payload["custom_character_url"] = st.session_state.flow_data[
                        "custom_character_url"
                    ]
                else:
                    api_payload["prebuild_character_choice"] = st.session_state.flow_data[
                        "prebuild_character_choice"
                    ]

                if st.session_state.flow_data["dialog_choice"] == "1":
                    api_payload["custom_dialog"] = st.session_state.flow_data[
                        "custom_dialog"
                    ]

                # Start real-time UGC streaming (this will block until completion)
                stream_ugc_execution_realtime(api_payload, status_placeholder, progress_placeholder, events_placeholder)
            else:  # Product Ad
                api_payload = {
                    "product_url": st.session_state.flow_data["product_url"],
                    "ad_prompt": st.session_state.flow_data["ad_prompt"],
                }
                
                # Start Product Ad execution
                stream_product_ad_execution(api_payload, status_placeholder, progress_placeholder, events_placeholder)
            
            # Reset streaming flag for next time
            st.session_state.streaming_started = False
            
            # Trigger rerun to show completed state
            st.rerun()
        else:
            # Show current status while streaming
            with events_placeholder.container():
                if st.session_state.streaming_events:
                    st.markdown("### 🔍 Live Events Log")
                    recent_events = st.session_state.streaming_events[-5:]
                    for event in reversed(recent_events):
                        event_type = event.get("type", "unknown")
                        event_message = event.get("message", str(event))
                        event_time = event.get("timestamp", "")
                        
                        if event_type == "error":
                            st.error(f"[{event_time}] ❌ {event_message}")
                        elif event_type in ["step_completed", "video_completed", "plan_completed"]:
                            st.success(f"[{event_time}] ✅ {event_message}")
                        elif event_type in ["step_started", "video_polling_started"]:
                            st.info(f"[{event_time}] ⏳ {event_message}")
                        else:
                            st.write(f"[{event_time}] 📍 {event_type}: {event_message}")

    elif st.session_state.execution_status == "completed":
        if st.session_state.ad_type_choice == "1":
            st.markdown(
                '''
                <div class="status-completed">
                    <h3 style="margin: 0; color: #065f46;">🎉 UGC Generation Completed!</h3>
                    <p style="margin: 0.5rem 0 0 0; color: #065f46;">Your UGC advertisement has been successfully created.</p>
                </div>
                ''',
                unsafe_allow_html=True
            )
            success_message = "✅ UGC generation completed successfully!"
        else:
            st.markdown(
                '''
                <div class="status-completed">
                    <h3 style="margin: 0; color: #065f46;">🎉 Product Ad Generation Completed!</h3>
                    <p style="margin: 0.5rem 0 0 0; color: #065f46;">Your product advertisement has been successfully created.</p>
                </div>
                ''',
                unsafe_allow_html=True
            )
            success_message = "✅ Product Ad generation completed successfully!"

        # Final progress bar
        st.progress(1.0)
        st.success(success_message)

        if st.session_state.final_video_url:
            st.markdown(
                '''
                <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                            padding: 2rem; border-radius: 15px; margin: 2rem 0;
                            border: 1px solid #e2e8f0;">
                    <h3 style="color: #1e293b; margin-bottom: 1rem; text-align: center;">🎥 Your Generated Video</h3>
                </div>
                ''',
                unsafe_allow_html=True
            )
            st.video(st.session_state.final_video_url)
            st.success(f"📹 **Video URL:** {st.session_state.final_video_url}")
        else:
            st.info("✅ Plan execution completed. Check the events log for details.")
            if st.session_state.prediction_id:
                st.info(f"🔍 Prediction ID: {st.session_state.prediction_id}")

        # Show final events summary
        if st.session_state.streaming_events:
            with st.expander("📊 Complete Events Log", expanded=False):
                for event in st.session_state.streaming_events:
                    event_type = event.get("type", "unknown")
                    event_time = event.get("timestamp", "")
                    event_message = event.get("message", str(event))
                    st.write(f"[{event_time}] {event_type}: {event_message}")

        # Social Sharing Option (only for UGC ads)
        if st.session_state.ad_type_choice == "1" and st.session_state.show_social_sharing and st.session_state.final_video_url:
            st.write("### 📱 Share on Social Media")
            st.info("Your video is ready! Would you like to create social media posts and schedule them?")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📱 Create Social Posts", type="primary", use_container_width=True):
                    # Switch to social sharing workflow
                    st.session_state.current_step = "social_sharing"
                    st.session_state.execution_status = "idle"
                    st.rerun()
            with col2:
                if st.button("🔄 Start New Generation", type="secondary", use_container_width=True):
                    reset_flow()
                    st.rerun()
            with col3:
                back_button_text = "← Back to Dialog" if st.session_state.ad_type_choice == "1" else "← Back to Ad Prompt"
                back_step = "dialog_generation" if st.session_state.ad_type_choice == "1" else "ad_prompt"
                if st.button(back_button_text, type="secondary", use_container_width=True):
                    st.session_state.current_step = back_step
                    st.session_state.execution_status = "idle"
                    st.rerun()
        else:
            # Original action buttons (when social sharing not available or Product Ad)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Start New Generation", type="primary"):
                    reset_flow()
                    st.rerun()
            with col2:
                back_button_text = "← Back to Dialog" if st.session_state.ad_type_choice == "1" else "← Back to Ad Prompt"
                back_step = "dialog_generation" if st.session_state.ad_type_choice == "1" else "ad_prompt"
                if st.button(back_button_text, type="secondary"):
                    st.session_state.current_step = back_step
                    st.session_state.execution_status = "idle"
                    st.rerun()

    elif st.session_state.execution_status == "error":
        st.markdown(
            '''
            <div class="status-error">
                <h3 style="margin: 0; color: #991b1b;">❌ Execution Error</h3>
                <p style="margin: 0.5rem 0 0 0; color: #991b1b;">An error occurred during execution. Check the events log for details.</p>
            </div>
            ''',
            unsafe_allow_html=True
        )

        # Show error progress
        st.progress(st.session_state.progress)
        st.write(f"**Error Status:** {st.session_state.current_step_name}")

        if st.session_state.streaming_events:
            with st.expander("📊 Error Events Log", expanded=True):
                for event in st.session_state.streaming_events[
                    -5:
                ]:  # Show last 5 events
                    event_type = event.get("type", "unknown")
                    event_time = event.get("timestamp", "")
                    event_message = event.get("message", str(event))

                    if event_type == "error":
                        st.error(f"[{event_time}] ❌ {event_message}")
                    else:
                        st.write(f"[{event_time}] {event_type}: {event_message}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Try Again", type="primary"):
                st.session_state.execution_status = "idle"
                st.session_state.streaming_events = []
                st.session_state.progress = 0.0
                st.session_state.current_step_name = "Ready to start"
                st.rerun()
        with col2:
            back_button_text = "← Back to Dialog" if st.session_state.ad_type_choice == "1" else "← Back to Ad Prompt"
            back_step = "dialog_generation" if st.session_state.ad_type_choice == "1" else "ad_prompt"
            if st.button(back_button_text, type="secondary"):
                st.session_state.current_step = back_step
                st.session_state.execution_status = "idle"
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Step 5: Social Sharing
elif st.session_state.current_step == "social_sharing":
    st.markdown('<div class="step-title">📱 Social Media Sharing</div>', unsafe_allow_html=True)
    st.markdown("Transform your video into engaging social media posts with automated scheduling")
    
    if not st.session_state.final_video_url:
        st.error("❌ No video available for social sharing. Please complete UGC generation first.")
        if st.button("← Back to Execution"):
            st.session_state.current_step = "execution"
            st.rerun()
    else:
        st.success(f"✅ Video ready for social sharing: {st.session_state.final_video_url}")
        
        # Show video preview
        with st.expander("🎥 Video Preview", expanded=True):
            st.video(st.session_state.final_video_url)
        
        # Social sharing prompt
        st.markdown(
            '''
            <div style="background: linear-gradient(135deg, #764ba2 0%, #764ba2 100%);
                        padding: 1.5rem; border-radius: 12px; margin: 1.5rem 0;
                        border-left: 4px solid #0ea5e9;">
                <h3 style="color: #f8fafc!; margin-bottom: 1rem;">📝 Social Media Posting Instructions</h3>
                <p style="color: #f8fafc; margin: 0;">Tell us how and when you'd like to share your content</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        st.markdown(
            '''
            <div style="background: #764ba2; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <h4 style="color: #1e293b; margin-bottom: 0.5rem;">💡 Example Instructions:</h4>
                <ul style="color: #1e293b; margin: 0; padding-left: 1.5rem;">
                    <li>"Post this to Instagram tomorrow at 3pm"</li>
                    <li>"Share on Twitter and Instagram now"</li>
                    <li>"Schedule for both platforms in 2 hours"</li>
                </ul>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        social_prompt = st.text_area(
            "🎯 Enter your posting instructions:",
            placeholder="Describe when and where you want to post your content...",
            height=100,
            key="social_prompt_input"
        )
        
        # Execution buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Start Social Scheduling", type="primary", use_container_width=True):
                if social_prompt.strip():
                    # Prepare social scheduler request
                    st.session_state.social_sharing_data = {
                        "user_prompt": social_prompt.strip(),
                        "media_url": st.session_state.final_video_url,
                        "product_description": st.session_state.generated_product_description or "UGC Video Product",
                        "dialog": st.session_state.generated_dialog or "Video Dialog Content"
                    }
                    st.session_state.execution_status = "running"
                    st.rerun()
                else:
                    st.warning("⚠️ Please enter a social media posting prompt")
        
        with col2:
            if st.button("← Back to UGC Results", type="secondary", use_container_width=True):
                st.session_state.current_step = "execution"
                st.rerun()
        
        # Handle running state for social sharing
        if st.session_state.execution_status == "running":
            st.write("### 🔄 Creating Social Media Posts...")
            
            # Create placeholders for real-time updates
            progress_placeholder = st.empty()
            status_placeholder = st.empty() 
            content_placeholder = st.empty()
            clarification_placeholder = st.empty()
            
            # Show initial progress
            with progress_placeholder.container():
                st.progress(0.1)
            
            with status_placeholder.container():
                st.info("⏳ Analyzing video content and generating social media captions...")
            
            # Start social scheduler execution
            social_data = st.session_state.social_sharing_data
            
            try:
                # Make API request to social scheduler
                response = requests.post(
                    f"{API_BASE_URL}/execute-social-scheduler-realtime",
                    json=social_data,
                    stream=True,
                    timeout=600
                )
                
                if response.status_code == 200:
                    events = []
                    clarification_data = None
                    plan_run_id = None
                    generated_captions = None
                    
                    for line in response.iter_lines():
                        if line:
                            line_str = line.decode("utf-8")
                            # Handle cases where multiple SSE events are in one line
                            if line_str.count("data:") > 1:
                                # Multiple events in one chunk
                                chunk_events = parse_sse_chunk(line_str)
                                for event in chunk_events:
                                    if event:
                                        events.append(event)
                            else:
                                # Single event
                                event = parse_sse_line(line_str)
                                if event:
                                    events.append(event)
                            
                            # Process the last added event for UI updates
                            if events:
                                event = events[-1]
                                event_type = event.get("type", "")
                                progress = 0.1
                                
                                # Handle the new execution hook events
                                if event_type == "started":
                                    with status_placeholder.container():
                                        st.info("⏳ Starting social media scheduling...")
                                    progress = 0.1
                                
                                elif event_type == "step_started":
                                    step_name = event.get("step_name", "")
                                    if "social media platform detector" in step_name.lower():
                                        status_msg = "⏳ Detecting target platform..."
                                        progress = 0.2
                                    elif "replicate gpt-4o" in step_name.lower():
                                        status_msg = "⏳ Generating social media captions..."
                                        progress = 0.4
                                    elif "extract" in step_name.lower() and "time" in step_name.lower():
                                        status_msg = "⏳ Extracting scheduling time..."
                                        progress = 0.6
                                    else:
                                        status_msg = f"⏳ {event.get('message', 'Processing step...')}"
                                        progress = min(progress + 0.15, 0.8)
                                    
                                    with status_placeholder.container():
                                        st.info(status_msg)
                                    with progress_placeholder.container():
                                        st.progress(progress)
                                
                                elif event_type == "step_completed":
                                    step_name = event.get("step_name", "")
                                    output = event.get("output", "")
                                    
                                    if "social media platform detector" in step_name.lower():
                                        platform = output.split('=')[1].split()[0] if '=' in output else 'Unknown'
                                        status_msg = f"✅ Platform detected: {platform}"
                                        progress = 0.3
                                    elif "replicate gpt-4o" in step_name.lower():
                                        status_msg = "✅ Social media captions generated!"
                                        progress = 0.7
                                        
                                        # Try to parse the output to show generated content
                                        # The output might be a JSON string or object
                                        try:
                                            if isinstance(output, str):
                                                # Try to find JSON-like content in the output
                                                import re
                                                json_match = re.search(r'\{.*\}', output)
                                                if json_match:
                                                    captions_data = json.loads(json_match.group())
                                                else:
                                                    captions_data = {"generated": output[:200]}
                                            else:
                                                captions_data = output
                                            
                                            with content_placeholder.container():
                                                st.write("### 🎨 Generated Content Preview")
                                                if captions_data.get("instagram_caption"):
                                                    st.info(f"📱 Instagram: {captions_data['instagram_caption']}")
                                                if captions_data.get("twitter_post"):
                                                    st.info(f"🐦 Twitter: {captions_data['twitter_post']}")
                                                if captions_data.get("channel"):
                                                    st.info(f"📺 Channel: {captions_data['channel']}")
                                                
                                        except (json.JSONDecodeError, AttributeError):
                                            # If we can't parse, just show a generic message
                                            with content_placeholder.container():
                                                st.write("### 🎨 Content Generated")
                                                st.info("Social media captions have been created!")
                                    
                                    elif "extract" in step_name.lower() and "time" in step_name.lower():
                                        status_msg = "✅ Scheduling time extracted"
                                        progress = 0.8
                                    else:
                                        status_msg = f"✅ {event.get('message', 'Step completed')}"
                                        progress = min(progress + 0.15, 0.9)
                                    
                                    with status_placeholder.container():
                                        st.success(status_msg)
                                    with progress_placeholder.container():
                                        st.progress(progress)
                                
                                elif event_type == "completed":
                                    # Final completion - this is the new event type from our API
                                    with progress_placeholder.container():
                                        st.progress(1.0)
                                    with status_placeholder.container():
                                        st.success("✅ Social media posts created successfully!")
                                    
                                    # Show final results
                                    with content_placeholder.container():
                                        st.write("### 🎉 Social Media Content Created")
                                        
                                        if event.get("instagram_caption"):
                                            st.success(f"📱 **Instagram:** {event['instagram_caption']}")
                                        
                                        if event.get("twitter_post"):
                                            st.success(f"🐦 **Twitter:** {event['twitter_post']}")
                                        
                                        if event.get("scheduled_time"):
                                            st.info(f"⏰ **Scheduled for:** {event['scheduled_time']}")
                                        
                                        st.write(f"📺 **Channel(s):** {event.get('channel', 'both')}")
                                    
                                    st.session_state.execution_status = "completed"
                                    break
                                
                                elif event_type == "error":
                                    with status_placeholder.container():
                                        st.error(f"❌ Error: {event.get('message', 'Unknown error')}")
                                    st.session_state.execution_status = "error"
                                    break
                    
                    # Streaming completed - trigger rerun to show final state
                    st.rerun()
                    
                else:
                    st.error(f"❌ API Error: {response.status_code} - {response.text}")
                    st.session_state.execution_status = "idle"
                    
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Connection error: {str(e)}")
                st.session_state.execution_status = "error"
        
        # Handle social sharing completion state
        elif st.session_state.execution_status == "completed":
            st.markdown(
                '''
                <div class="status-completed">
                    <h3 style="margin: 0; color: #065f46;">🎉 Social Media Success!</h3>
                    <p style="margin: 0.5rem 0 0 0; color: #065f46;">Your social media posts have been created and scheduled successfully.</p>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔄 Create New Posts", type="primary", use_container_width=True):
                    st.session_state.execution_status = "idle"
                    st.session_state.social_sharing_data = {}
                    st.rerun()
            with col2:
                if st.button("← Back to UGC Results", type="secondary", use_container_width=True):
                    st.session_state.current_step = "execution"
                    st.session_state.execution_status = "idle"
                    st.rerun()
            with col3:
                if st.button("🔄 Start New Generation", type="secondary", use_container_width=True):
                    reset_flow()
                    st.rerun()
        
        # Handle social sharing error state
        elif st.session_state.execution_status == "error":
            st.markdown(
                '''
                <div class="status-error">
                    <h3 style="margin: 0; color: #991b1b;">❌ Social Media Error</h3>
                    <p style="margin: 0.5rem 0 0 0; color: #991b1b;">An error occurred during social media posting. Please try again.</p>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Try Again", type="primary", use_container_width=True):
                    st.session_state.execution_status = "idle"
                    st.rerun()
            with col2:
                if st.button("← Back to UGC Results", type="secondary", use_container_width=True):
                    st.session_state.current_step = "execution"
                    st.session_state.execution_status = "idle"
                    st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Enhanced Sidebar with status and controls
with st.sidebar:
    st.markdown(
        '''
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 1rem; border-radius: 10px; margin-bottom: 2rem;
                    text-align: center;">
            <h2 style="color: white; margin: 0; font-family: 'Inter', sans-serif;">🔧 System Status</h2>
        </div>
        ''',
        unsafe_allow_html=True
    )

    # Enhanced API Status - use cached status
    if st.session_state.get("api_status_checked", False):
        st.markdown(
            '''
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 1rem; border-radius: 8px; margin: 1rem 0; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                <p style="margin: 0; color: #f0fdf4; font-weight: 600; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);">✅ API Server: Online</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '''
            <div style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 1rem; border-radius: 8px; margin: 1rem 0; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                <p style="margin: 0; color: #fef2f2; font-weight: 600; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);">❌ API Server: Offline</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        if st.button("🔄 Check API", key="sidebar_api_check"):
            st.session_state.api_status_checked = check_api_health()
            st.rerun()

    # Execution Status
    status_emoji = {"idle": "⏸️", "running": "🔄", "completed": "✅", "error": "❌"}
    st.write(
        f"**Execution Status:** {status_emoji.get(st.session_state.execution_status, '❓')} {st.session_state.execution_status.title()}"
    )

    # Current progress
    if st.session_state.execution_status == "running":
        st.write(f"**Progress:** {st.session_state.progress:.1%}")
        st.write(f"**Current:** {st.session_state.current_step_name}")

    # Current flow data
    if st.session_state.flow_data:
        st.write("**Current Flow:**")
        st.write(f"- Step: {st.session_state.current_step}")
        if st.session_state.ad_type_choice:
            ad_type_name = "UGC Ad" if st.session_state.ad_type_choice == "1" else "Product Ad"
            st.write(f"- Ad Type: {ad_type_name}")
        st.write(f"- Data Keys: {list(st.session_state.flow_data.keys())}")

        if st.session_state.streaming_events:
            st.write(f"- Events: {len(st.session_state.streaming_events)}")

        if st.session_state.prediction_id:
            st.write(f"- Prediction: {st.session_state.prediction_id[:8]}...")

    st.write("---")

   
    cloudinary_status = '✅' if all([os.getenv('CLOUDINARY_CLOUD_NAME'), os.getenv('CLOUDINARY_API_KEY'), os.getenv('CLOUDINARY_API_SECRET')]) else '❌'
    # ✅ Cloudinary Configuration
    st.markdown(
        f'''
        <div style="background: linear-gradient(135deg, {'#10b981 0%, #059669 100%' if cloudinary_status == '✅' else '#f59e0b 0%, #d97706 100%'}); 
                    padding: 0.75rem; border-radius: 6px; margin: 0.5rem 0; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);">
            <p style="margin: 0; color: {'#f0fdf4' if cloudinary_status == '✅' else '#fefbf0'}; font-size: 0.9rem; font-weight: 500; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);">
                {cloudinary_status} Cloudinary Configuration
            </p>
        </div>
        ''',
        unsafe_allow_html=True
    )

    st.write("---")

    # Controls
    if st.button("🔄 Reset Everything", type="secondary", use_container_width=True):
        reset_flow()
        st.rerun()

    if st.button("🔍 Refresh Status", use_container_width=True):
        st.rerun()