# 📡 UGC Generator - Streaming Setup

This document explains how to use the real-time plan execution streaming feature.

## 🚀 Quick Start

### 1. Start the Stream Viewer (Terminal 1)

```bash
cd character-flow
streamlit run stream_viewer.py
```

### 2. Run the Main Application (Terminal 2)

```bash
cd character-flow
python main.py
```

### 3. Watch the Magic! ✨

- The stream viewer will automatically update as your plan executes
- You'll see real-time progress, step details, and outputs

## 📋 Features

### Stream Viewer App (`stream_viewer.py`)

- **Real-time Progress**: See current step and overall progress
- **Step Details**: Expandable sections showing step status, duration, and outputs
- **Auto-refresh**: Automatically updates every second during plan execution
- **Manual Controls**: Refresh manually or clear the stream file
- **Responsive UI**: Clean, organized display with progress bars and status indicators

### Streaming Hooks (`utils/streaming_hooks.py`)

- **Before Plan Run**: Initializes the stream with plan metadata
- **Before Step**: Updates current step status and details
- **After Step**: Records step completion, duration, and outputs
- **After Last Step**: Marks plan as completed

### Stream Data Format (`plan_stream.json`)

```json
{
  "status": "running|completed|waiting|error",
  "plan_name": "UGC Generator - Character and Product Setup with Replicate",
  "total_steps": 8,
  "current_step": 3,
  "started_at": "2025-08-23T10:30:00",
  "steps": [
    {
      "step_number": 1,
      "task": "Get character URL",
      "tool_id": "function",
      "status": "completed",
      "started_at": "2025-08-23T10:30:01",
      "completed_at": "2025-08-23T10:30:02",
      "output": "https://character-url.com"
    }
  ]
}
```

## 🎛️ Controls

### Stream Viewer Interface

- **🔄 Auto Refresh**: Toggle automatic updates (enabled by default)
- **🔄 Refresh Now**: Manually refresh the display
- **🗑️ Clear Stream**: Remove the stream file to reset

### Status Indicators

- 🟡 **Waiting**: Plan not started yet
- 🟢 **Running**: Plan currently executing
- ✅ **Completed**: Plan finished successfully
- ❌ **Error**: Plan encountered an error

### Step Status Icons

- ⏳ **Pending**: Step not started
- 🔄 **Running**: Step currently executing
- ✅ **Completed**: Step finished successfully
- ❌ **Error**: Step failed

## 🔧 Technical Details

### File-Based Streaming

- Uses `plan_stream.json` for communication between main app and viewer
- Updates written after each step completion
- Safe for concurrent access (JSON reads/writes)

### Execution Hooks Integration

- Integrated into `utils/config.py`
- Automatically active when running `main.py`
- No additional setup required

### Performance

- Minimal overhead (file I/O only)
- 1-second refresh interval (configurable)
- Handles long-running plans gracefully

## 📱 Usage Tips

1. **Keep Stream Viewer Open**: Leave the browser tab open to see real-time updates
2. **Multiple Viewers**: You can open multiple browser tabs to watch the same stream
3. **Clear Between Runs**: Use "Clear Stream" button to reset for new plan runs
4. **Step Details**: Click on step sections to see detailed outputs and timings

## 🐛 Troubleshooting

### Stream Not Updating

- Check if `plan_stream.json` exists in the character-flow directory
- Ensure `main.py` is running and executing the plan
- Try manual refresh or restart the stream viewer

### Permission Errors

- Ensure write permissions for the character-flow directory
- Check if `plan_stream.json` is not locked by another process

### Browser Issues

- Hard refresh (Ctrl+F5) the stream viewer page
- Clear browser cache if needed
- Try a different browser

## 🚀 Next Steps

This is the basic implementation. Potential enhancements:

- WebSocket integration for even faster updates
- Error handling and retry mechanisms
- Historical plan run storage
- Export/import of plan execution data
- Integration with the main Streamlit app
