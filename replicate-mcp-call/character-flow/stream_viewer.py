import streamlit as st
import json
import time
import os
from datetime import datetime, timedelta

# Configure page
st.set_page_config(
    page_title="📡 Plan Stream Viewer",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.title("📡 UGC Generator - Plan Execution Stream")

# Settings
STREAM_FILE = os.path.join(os.path.dirname(__file__), "plan_stream.json")
REFRESH_INTERVAL = 1  # seconds

# Initialize session state
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if "last_mtime" not in st.session_state:
    st.session_state.last_mtime = 0.0


def trigger_rerun():
    """Trigger a Streamlit rerun with compatibility fallback."""
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()  # For older Streamlit versions
        except Exception:
            pass


def load_stream_data():
    """Load the latest stream data from file"""
    try:
        if os.path.exists(STREAM_FILE):
            with open(STREAM_FILE, "r") as f:
                return json.load(f)
        else:
            return {
                "status": "no_file",
                "message": "Stream file not found. Start the main app to begin streaming.",
            }
    except Exception as e:
        return {"status": "error", "message": f"Error reading stream file: {str(e)}"}


def format_datetime(datetime_str):
    """Format datetime string for display"""
    try:
        dt = datetime.fromisoformat(datetime_str)
        return dt.strftime("%H:%M:%S")
    except:
        return datetime_str


def calculate_duration(start_time_str, end_time_str=None):
    """Calculate duration between two datetime strings"""
    try:
        start = datetime.fromisoformat(start_time_str)
        end = datetime.fromisoformat(end_time_str) if end_time_str else datetime.now()
        duration = end - start
        return f"{duration.total_seconds():.1f}s"
    except:
        return "Unknown"


# Sidebar controls
with st.sidebar:
    st.header("🎛️ Controls")

    # Auto-refresh toggle
    auto_refresh = st.checkbox("🔄 Auto Refresh", value=st.session_state.auto_refresh)
    st.session_state.auto_refresh = auto_refresh

    # Manual refresh button
    if st.button("🔄 Refresh Now", type="primary"):
        st.session_state.last_refresh = datetime.now()
        trigger_rerun()

    # Clear stream file
    if st.button("🗑️ Clear Stream", type="secondary"):
        try:
            if os.path.exists(STREAM_FILE):
                os.remove(STREAM_FILE)
                st.success("Stream file cleared!")
                trigger_rerun()
        except Exception as e:
            st.error(f"Error clearing stream: {e}")

    st.divider()

    # Settings
    st.subheader("⚙️ Settings")
    st.write(f"📁 Stream File: `{STREAM_FILE}`")
    st.write(f"⏱️ Refresh Interval: {REFRESH_INTERVAL}s")
    st.write(f"🕐 Last Refresh: {st.session_state.last_refresh.strftime('%H:%M:%S')}")

# Load current stream data
stream_data = load_stream_data()

# Main content
if stream_data.get("status") == "no_file":
    st.info("🔍 Waiting for stream data...")
    st.write("**Instructions:**")
    st.write("1. Run `python main.py` in the character-flow directory")
    st.write("2. The stream will appear here automatically")
    st.write("3. Keep this page open to watch the plan execution progress")

elif stream_data.get("status") == "error":
    st.error(f"❌ {stream_data.get('message')}")

else:
    # Plan overview
    status = stream_data.get("status", "unknown")
    plan_name = stream_data.get("plan_name", "Unknown Plan")
    total_steps = stream_data.get("total_steps", 0)
    current_step = stream_data.get("current_step", 0)

    # Status indicator
    status_colors = {"waiting": "🟡", "running": "🟢", "completed": "✅", "error": "❌"}

    status_color = status_colors.get(status, "⚪")

    st.subheader(f"{status_color} Plan Status: {status.title()}")

    # Plan info
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📋 Plan Name", plan_name)

    with col2:
        if total_steps > 0:
            progress_pct = (current_step / total_steps) * 100
            st.metric(
                "📊 Progress", f"{current_step}/{total_steps}", f"{progress_pct:.1f}%"
            )
        else:
            st.metric("📊 Progress", "0/0", "0%")

    with col3:
        started_at = stream_data.get("started_at")
        if started_at:
            duration = calculate_duration(started_at, stream_data.get("completed_at"))
            st.metric("⏱️ Duration", duration)
        else:
            st.metric("⏱️ Duration", "Not started")

    # Progress bar
    if total_steps > 0:
        progress = current_step / total_steps
        st.progress(progress, f"Step {current_step} of {total_steps}")

    # Current step info
    if status == "running":
        current_step_name = stream_data.get("current_step_name", "Unknown")
        current_step_tool = stream_data.get("current_step_tool", "Unknown")

        st.info(
            f"🔄 Currently running: **{current_step_name}** (Tool: {current_step_tool})"
        )

    # Steps details
    steps = stream_data.get("steps", [])
    if steps:
        st.subheader("📝 Step Details")

        for i, step in enumerate(steps):
            step_status = step.get("status", "pending")
            step_task = step.get("task", f"Step {i+1}")
            step_tool = step.get("tool_id", "unknown")

            # Step status icon
            step_icons = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "error": "❌",
            }
            step_icon = step_icons.get(step_status, "⚪")

            # Expandable step details
            with st.expander(
                f"{step_icon} Step {i+1}: {step_task}",
                expanded=(step_status == "running"),
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Status:** {step_status.title()}")
                    st.write(f"**Tool:** {step_tool}")

                    if step.get("started_at"):
                        st.write(f"**Started:** {format_datetime(step['started_at'])}")

                    if step.get("completed_at"):
                        st.write(
                            f"**Completed:** {format_datetime(step['completed_at'])}"
                        )
                        duration = calculate_duration(
                            step.get("started_at"), step.get("completed_at")
                        )
                        st.write(f"**Duration:** {duration}")

                with col2:
                    if step.get("output"):
                        st.write("**Output:**")
                        st.code(step["output"], language="json")

                    if step.get("error"):
                        st.write("**Error:**")
                        st.error(step["error"])

# Auto-refresh logic: trigger rerun on interval or file change
should_refresh = False
if st.session_state.auto_refresh:
    # Refresh on interval when in active states
    if stream_data.get("status") in ["waiting", "running"]:
        if datetime.now() - st.session_state.last_refresh > timedelta(
            seconds=REFRESH_INTERVAL
        ):
            st.session_state.last_refresh = datetime.now()
            should_refresh = True

    # Refresh when file modified
    try:
        mtime = os.path.getmtime(STREAM_FILE) if os.path.exists(STREAM_FILE) else 0.0
        if mtime != st.session_state.last_mtime:
            st.session_state.last_mtime = mtime
            should_refresh = True
    except Exception:
        pass

if should_refresh:
    time.sleep(0.05)
    trigger_rerun()

# Footer
st.divider()
st.caption(f"🕐 Last updated: {stream_data.get('last_updated', 'Unknown')}")
