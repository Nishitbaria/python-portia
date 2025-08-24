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
st.set_page_config(page_title="🎬 UGC Generator", page_icon="🎬", layout="wide")

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

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    
    .status-container {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .status-running {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
    }
    
    .status-completed {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
    }
    
    .status-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
    }
    
    .event-log {
        max-height: 300px;
        overflow-y: auto;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 5px;
        font-family: monospace;
        font-size: 0.9em;
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
        st.session_state.current_step = "character_selection"
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
    st.session_state.current_step = "character_selection"
    st.session_state.flow_completed = False
    st.session_state.execution_status = "idle"
    st.session_state.streaming_events = []
    st.session_state.final_video_url = None
    st.session_state.prediction_id = None
    st.session_state.progress = 0.0
    st.session_state.current_step_name = "Not started"
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


def stream_ugc_execution_realtime(payload: Dict[str, Any], status_placeholder, progress_placeholder, events_placeholder):
    """Stream UGC execution with real-time UI updates using placeholders"""
    try:
        # Make streaming request
        response = requests.post(
            f"{API_BASE_URL}/execute-ugc-realtime",
            json=payload,
            stream=True,
            timeout=600,  # 10 minute timeout
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


def stream_ugc_execution(payload: Dict[str, Any]):
    """Legacy function - kept for compatibility"""
    # This is the old function that used threading - now we use the real-time version
    pass


# Main title
st.markdown(
    '<h1 class="main-header">🎬 UGC Generator with Live Progress</h1>',
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

# Show progress
steps = [
    "Character Selection",
    "Product Image",
    "Dialog Generation",
    "Execute & Monitor",
]
current_step_index = {
    "character_selection": 0,
    "product_image": 1,
    "dialog_generation": 2,
    "execution": 3,
}.get(st.session_state.current_step, 0)

st.progress((current_step_index + 1) / len(steps))
st.write(
    f"**Step {current_step_index + 1} of {len(steps)}: {steps[current_step_index]}**"
)

# Step 1: Character Selection
if st.session_state.current_step == "character_selection":
    st.header("=== Character Selection ===")

    character_choice = st.radio(
        "Choose your character option:",
        ["1. Bring your own character", "2. Use prebuild characters"],
        key="character_choice_radio",
    )

    if character_choice == "1. Bring your own character":
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

    elif character_choice == "2. Use prebuild characters":
        st.write("🎭 You chose to use prebuild characters")
        st.write("Choose from the following characters:")

        # Initialize selected character if not exists
        if "selected_character_index" not in st.session_state:
            st.session_state.selected_character_index = None

        # Display character options in a grid
        cols = st.columns(3)  # 3 columns for better layout

        for i, url in enumerate(PREDEFINED_CHARACTERS):
            col_index = i % 3
            with cols[col_index]:
                # Check if this character is currently selected
                is_selected = st.session_state.selected_character_index == i

                try:
                    st.image(url, caption=f"Character {i+1}", width=150)
                except:
                    st.write(f"Character {i+1}")
                    st.write(f"[Image preview unavailable]")

                # Selection button with visual feedback
                button_type = "primary" if is_selected else "secondary"
                button_label = (
                    f"✅ Selected" if is_selected else f"Select Character {i+1}"
                )

                if st.button(
                    button_label,
                    key=f"select_char_{i}",
                    type=button_type,
                    use_container_width=True,
                ):
                    if not is_selected:  # Only update if not already selected
                        st.session_state.selected_character_index = i
                        st.rerun()

        # Show selected character
        if st.session_state.selected_character_index is not None:
            selected_index = st.session_state.selected_character_index
            st.success(f"✅ Selected: Character {selected_index + 1}")

            if st.button(
                "Confirm Character Selection", type="primary", use_container_width=True
            ):
                st.session_state.flow_data["character_choice"] = "2"
                st.session_state.flow_data["prebuild_character_choice"] = (
                    selected_index + 1
                )
                st.session_state.flow_data["character_url"] = PREDEFINED_CHARACTERS[
                    selected_index
                ]
                st.session_state.current_step = "product_image"
                # Clean up selection state
                if "selected_character_index" in st.session_state:
                    del st.session_state.selected_character_index
                st.rerun()

# Step 2: Product Image
elif st.session_state.current_step == "product_image":
    st.header("=== Product Image ===")
    st.write(
        "Please provide your product image. You can either upload a file or enter a URL."
    )

    product_option = st.radio(
        "Choose how to provide your product image:",
        ["Upload file (will be uploaded to Cloudinary)", "Enter URL directly"],
        key="product_option_radio",
    )

    if product_option == "Upload file (will be uploaded to Cloudinary)":
        uploaded_file = st.file_uploader(
            "Choose a product image...",
            type=["png", "jpg", "jpeg", "gif", "bmp", "webp"],
            key="product_file_upload",
        )

        if uploaded_file:
            st.image(uploaded_file, caption="Product Image Preview", width=300)

            if st.button("Upload to Cloudinary", type="primary"):
                product_url = upload_to_cloudinary(uploaded_file)
                if product_url:
                    st.session_state.flow_data["product_image_source"] = "upload"
                    st.session_state.flow_data["product_url"] = product_url
                    st.session_state.current_step = "dialog_generation"
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
                    st.session_state.current_step = "dialog_generation"
                    st.rerun()
            else:
                st.error(
                    "❌ Please enter a valid URL (must start with http:// or https://)"
                )

    if st.button("← Back to Character Selection"):
        st.session_state.current_step = "character_selection"
        st.rerun()

# Step 3: Dialog Generation
elif st.session_state.current_step == "dialog_generation":
    st.header("=== Dialog Generation ===")

    dialog_choice = st.radio(
        "Choose your dialog option:",
        ["1. Enter custom dialog", "2. Auto generate dialog"],
        key="dialog_choice_radio",
    )

    if dialog_choice == "1. Enter custom dialog":
        st.write("📝 You chose to enter custom dialog")
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

    elif dialog_choice == "2. Auto generate dialog":
        st.write("🤖 You chose to auto generate dialog")

        if st.button("Confirm Auto Generate", type="primary"):
            st.session_state.flow_data["dialog_choice"] = "2"
            st.session_state.current_step = "execution"
            st.session_state.flow_completed = True
            st.rerun()

    if st.button("← Back to Product Image"):
        st.session_state.current_step = "product_image"
        st.rerun()

# Step 4: Execution & Monitoring
elif st.session_state.current_step == "execution":
    st.header("🚀 UGC Generation & Live Monitoring")

    # Display collected input summary
    with st.expander("📋 Input Summary", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
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

        with col2:
            st.write("**📦 Product:**")
            st.write(
                f"- Source: {st.session_state.flow_data.get('product_image_source', 'URL')}"
            )
            st.write(f"- URL: {st.session_state.flow_data.get('product_url', '')}")

    # Real-time execution status
    if st.session_state.execution_status == "idle":
        st.write("### Ready to Execute")

        if st.button(
            "🚀 Start UGC Generation", type="primary", use_container_width=True
        ):
            # Prepare API payload
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

            # Set execution status and clear previous events
            st.session_state.execution_status = "running"
            st.session_state.streaming_events = []
            st.session_state.final_video_url = None
            st.session_state.progress = 0.0
            st.session_state.current_step_name = "Starting..."

            # Start streaming with real-time updates using direct execution
            st.rerun()

    elif st.session_state.execution_status == "running":
        st.write("### 🔄 Execution in Progress...")

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
            
            # Prepare API payload from stored data
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

            # Start real-time streaming (this will block until completion)
            stream_ugc_execution_realtime(api_payload, status_placeholder, progress_placeholder, events_placeholder)
            
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
        st.write("### 🎉 Execution Completed!")

        # Final progress bar
        st.progress(1.0)
        st.success("✅ UGC generation completed successfully!")

        if st.session_state.final_video_url:
            st.write("### 🎥 Generated Video")
            st.video(st.session_state.final_video_url)
            st.info(f"📹 Video URL: {st.session_state.final_video_url}")
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

        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Start New Generation", type="primary"):
                reset_flow()
                st.rerun()
        with col2:
            if st.button("← Back to Inputs", type="secondary"):
                st.session_state.current_step = "dialog_generation"
                st.session_state.execution_status = "idle"
                st.rerun()

    elif st.session_state.execution_status == "error":
        st.write("### ❌ Execution Error")
        st.error(
            "An error occurred during execution. Check the events log for details."
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
            if st.button("← Back to Inputs", type="secondary"):
                st.session_state.current_step = "dialog_generation"
                st.session_state.execution_status = "idle"
                st.rerun()

# Sidebar with status and controls
with st.sidebar:
    st.header("🔧 System Status")

    # API Status - use cached status
    if st.session_state.get("api_status_checked", False):
        st.success("✅ API Server: Online")
    else:
        st.error("❌ API Server: Offline")
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
        st.write(f"- Data Keys: {list(st.session_state.flow_data.keys())}")

        if st.session_state.streaming_events:
            st.write(f"- Events: {len(st.session_state.streaming_events)}")

        if st.session_state.prediction_id:
            st.write(f"- Prediction: {st.session_state.prediction_id[:8]}...")

    st.write("---")

    # Environment Status
    st.write("**Environment:**")
    st.write(
        f"- Cloudinary: {'✅' if all([os.getenv('CLOUDINARY_CLOUD_NAME'), os.getenv('CLOUDINARY_API_KEY'), os.getenv('CLOUDINARY_API_SECRET')]) else '❌'}"
    )

    st.write("---")

    # Controls
    if st.button("🔄 Reset Everything", type="secondary", use_container_width=True):
        reset_flow()
        st.rerun()

    if st.button("🔍 Refresh Status", use_container_width=True):
        st.rerun()
