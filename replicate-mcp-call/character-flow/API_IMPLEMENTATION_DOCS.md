# UGC Generator API Implementation Documentation

## Overview

This document details the complete implementation of a FastAPI-based streaming API wrapper for the UGC Generator system. The API transforms the CLI-based UGC generation pipeline into a web service with real-time streaming capabilities and proper clarification handling.

## Table of Contents
- [Project Context](#project-context)
- [Implementation Summary](#implementation-summary)
- [API Architecture](#api-architecture)
- [Endpoint Documentation](#endpoint-documentation)
- [Streaming Implementation](#streaming-implementation)
- [Clarification Handling](#clarification-handling)
- [Error Handling & Logging](#error-handling--logging)
- [Request/Response Models](#requestresponse-models)
- [Usage Examples](#usage-examples)
- [Testing Guide](#testing-guide)
- [Technical Details](#technical-details)

## Project Context

### Original System (main.py)
The original UGC Generator is a CLI-based application that:
- Uses Portia framework with PlanBuilderV2 for AI workflow orchestration
- Integrates with Replicate API for AI model calls (avatar generation, GPT-4o, UGC video creation)
- Handles character selection (custom vs prebuild characters)
- Generates product descriptions and dialog using AI models
- Creates UGC videos through a multi-step pipeline
- Includes prediction polling for final video results
- Uses interactive CLI prompts for user input

### Implementation Requirements
Based on user requirements:
1. **Same inputs as CLI** - Keep existing input structure
2. **Clarification handling** - Send clarifications to client, resume via separate endpoint
3. **Simple implementation** - Keep it straightforward and maintainable
4. **Multiple streaming modes** - Basic streaming, real-time hooks, synchronous execution
5. **Complete functionality** - Include all original features plus API capabilities

## Implementation Summary

### Files Created
- **`api_server.py`** - Main FastAPI application with streaming endpoints

### Key Achievements
✅ **Complete API wrapper** for main.py UGC Generator  
✅ **Multiple execution modes** (sync, streaming, real-time)  
✅ **Clarification handling** with separate resolution endpoint  
✅ **Real-time streaming** with Server-Sent Events (SSE)  
✅ **Execution hooks integration** for granular progress updates  
✅ **Comprehensive error handling** and logging  
✅ **Video polling integration** for final results  
✅ **CORS support** for web clients  
✅ **Request validation** and input sanitization  

## API Architecture

### Core Components

1. **FastAPI Application** (`app`)
   - Main web server with async support
   - CORS headers for cross-origin requests
   - Comprehensive error handling middleware

2. **Portia Integration** 
   - Direct import from `main.py` for plan and configuration
   - Execution hooks for real-time streaming
   - Clarification management system

3. **Storage Systems**
   - `running_plans` - Active plan run storage
   - `plan_clarifications` - Clarification tracking for resolution

4. **Streaming Infrastructure**
   - Server-Sent Events (SSE) for real-time updates
   - Threading for non-blocking execution
   - Event queues for hook-based streaming

## Endpoint Documentation

### 1. `/execute-ugc` [POST] - Synchronous Execution
**Purpose**: Execute complete UGC generation and return final results

**Request Model**: `UGCGeneratorRequest`
```json
{
  "character_choice": "1|2",
  "custom_character_url": "string (optional)",
  "prebuild_character_choice": "int (optional)",
  "product_url": "string (required)",
  "dialog_choice": "1|2",
  "custom_dialog": "string (optional)",
  "system_prompt": "string (optional)",
  "dialog_system_prompt": "string (optional)"
}
```

**Response Model**: `UGCGeneratorResponse`
```json
{
  "plan_id": "string",
  "plan_run_id": "string", 
  "state": "string",
  "steps": [StepOutput],
  "final_output": UGC_Prediction,
  "video_url": "string (optional)"
}
```

**Features**:
- Complete execution from start to finish
- Automatic video polling after UGC generation
- Full error handling with detailed responses
- Comprehensive logging of execution steps

### 2. `/execute-ugc-stream` [POST] - Basic Streaming
**Purpose**: Stream UGC generation progress using polling approach

**Request Model**: `UGCGeneratorRequest` (same as above)

**Response**: Server-Sent Events (SSE) stream

**Event Types**:
```json
{"type": "plan_started", "plan_id": "...", "plan_run_id": "..."}
{"type": "step_output", "step_name": "...", "output": "...", "status": "completed"}
{"type": "clarification_needed", "clarifications": [...]}
{"type": "completed", "final_output": {...}}
{"type": "polling_started", "prediction_id": "..."}
{"type": "video_ready", "video_url": "..."}
{"type": "error", "message": "..."}
```

**Features**:
- Real-time step progress updates
- Clarification handling (pauses execution)
- Automatic video polling and streaming
- Error streaming with context
- Plan run cleanup after completion

### 3. `/execute-ugc-realtime` [POST] - Real-time Streaming with Hooks
**Purpose**: True real-time streaming using Portia execution hooks

**Request Model**: `UGCGeneratorRequest` (same as above)

**Response**: Server-Sent Events (SSE) stream

**Additional Event Types**:
```json
{"type": "step_started", "step_name": "...", "tool_id": "..."}
{"type": "step_completed", "step_name": "...", "output": "..."}
{"type": "video_polling_started", "prediction_id": "..."}
{"type": "video_completed", "video_url": "..."}
```

**Features**:
- Immediate step start/completion notifications
- Threading for non-blocking execution
- Event queue system for real-time updates
- Enhanced granular progress tracking
- Complete video generation workflow streaming

### 4. `/resolve-clarification/{plan_run_id}` [POST] - Clarification Resolution
**Purpose**: Resolve clarifications and resume plan execution

**Path Parameter**: `plan_run_id` - ID of the paused plan run

**Request Model**: `ClarificationResponse`
```json
{
  "clarification_id": "string",
  "response": "string"
}
```

**Response**:
```json
{
  "status": "resolved",
  "plan_run_id": "string",
  "clarification_id": "string", 
  "new_state": "string"
}
```

**Features**:
- Resolves specific clarifications by ID
- Resumes plan execution automatically
- Updates plan run state
- Cleanup of resolved clarifications

### 5. `/plan-status/{plan_run_id}` [GET] - Plan Status Check
**Purpose**: Get current status of a running plan

**Response**:
```json
{
  "plan_run_id": "string",
  "state": "string",
  "current_step_index": "int",
  "has_clarifications": "boolean"
}
```

### 6. `/prebuild-characters` [GET] - Character List
**Purpose**: Get available prebuild character URLs

**Response**:
```json
{
  "characters": [
    {"index": 1, "url": "https://..."},
    {"index": 2, "url": "https://..."}
  ]
}
```

### 7. `/health` [GET] - Health Check
**Purpose**: Service health monitoring

**Response**:
```json
{
  "status": "healthy",
  "service": "UGC Generator API"
}
```

## Streaming Implementation

### Server-Sent Events (SSE)
- **Media Type**: `text/event-stream`
- **Format**: `data: {JSON}\n\n`
- **Headers**: CORS-enabled, no-cache
- **Connection**: Keep-alive for real-time updates

### Streaming Strategies

#### 1. Polling-Based Streaming (`/execute-ugc-stream`)
```python
async def stream_ugc_execution(request: UGCGeneratorRequest):
    while plan_run.state not in [COMPLETE, FAILED]:
        if plan_run.state == IN_PROGRESS:
            # Extract step outputs
            # Stream progress updates
        elif plan_run.state == NEED_CLARIFICATION:
            # Send clarification events
            # Pause execution
        await asyncio.sleep(0.5)  # Polling interval
```

#### 2. Hook-Based Real-time Streaming (`/execute-ugc-realtime`)
```python
def before_step_hook(plan, plan_run, step):
    event_queue.put({
        "type": "step_started",
        "step_name": step.task,
        "plan_run_id": str(plan_run.id)
    })

def after_step_hook(plan, plan_run, step, output):
    event_queue.put({
        "type": "step_completed", 
        "output": str(output),
        "plan_run_id": str(plan_run.id)
    })
```

### Threading Architecture
- **Main Thread**: FastAPI async event streaming
- **Background Thread**: Portia plan execution with hooks
- **Communication**: Thread-safe queues for event passing
- **Synchronization**: Event-driven coordination between threads

## Clarification Handling

### Flow Overview
1. **Detection**: Plan execution encounters clarification need
2. **Storage**: Clarification stored in global `plan_clarifications` dict
3. **Streaming**: Clarification details sent via SSE to client
4. **Resolution**: Client calls `/resolve-clarification` endpoint
5. **Resumption**: Plan execution resumes with resolved values

### Clarification Storage Structure
```python
plan_clarifications[clarification_id] = {
    'clarification': clarification_object,
    'plan_run': plan_run_object
}
```

### Supported Clarification Types
- **MultipleChoiceClarification**: With options array
- **UserVerificationClarification**: Yes/no prompts
- **TextClarification**: Free text input
- **Custom clarifications**: With argument mapping

### Error Handling
- Invalid clarification IDs return 404
- Malformed responses return 400 with details
- Resolution failures are logged and reported

## Error Handling & Logging

### Logging Configuration
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Error Categories

#### 1. Validation Errors
- Invalid URLs (character, product)
- Missing required fields
- Invalid choice values
- Empty custom dialogs

#### 2. Execution Errors  
- Portia plan execution failures
- Replicate API errors
- Step execution timeouts
- Resource unavailability

#### 3. System Errors
- Threading failures
- Queue overflow
- Memory issues
- Network connectivity

### Error Response Format
```json
{
  "type": "error",
  "plan_run_id": "string (optional)",
  "message": "string",
  "error_code": "string (optional)",
  "details": "object (optional)"
}
```

### Logging Strategy
- **INFO**: Plan starts, completions, major milestones
- **WARNING**: Non-critical issues, fallback usage
- **ERROR**: Execution failures, API errors, system issues
- **DEBUG**: Step-by-step execution details (if enabled)

## Request/Response Models

### Core Request Model
```python
class UGCGeneratorRequest(BaseModel):
    character_choice: str  # "1" for custom, "2" for prebuild
    custom_character_url: Optional[str] = ""
    prebuild_character_choice: Optional[int] = 0
    product_url: str
    dialog_choice: str  # "1" for custom, "2" for auto generate
    custom_dialog: Optional[str] = ""
    system_prompt: Optional[str] = PRODUCT_DESCRIPTION_SYSTEM_PROMPT
    dialog_system_prompt: Optional[str] = DIALOG_GENERATION_SYSTEM_PROMPT
```

### Response Models
```python
class StepOutput(BaseModel):
    step_index: int
    step_name: str
    output: str
    status: str

class UGCGeneratorResponse(BaseModel):
    plan_id: str
    plan_run_id: str
    state: str
    steps: List[StepOutput]
    final_output: Optional[UGC_Prediction] = None
    video_url: Optional[str] = None

class ClarificationInfo(BaseModel):
    id: str
    category: str
    user_guidance: str
    argument_name: Optional[str] = None
    options: Optional[List[str]] = None
```

### Validation Rules
- **URLs**: Must start with `http://` or `https://`
- **Character Choice**: Must be "1" (custom) or "2" (prebuild)
- **Prebuild Selection**: Must be 1-9 (matching available characters)
- **Dialog Choice**: Must be "1" (custom) or "2" (auto-generate)
- **Custom Dialog**: Required if dialog_choice is "1", non-empty

## Usage Examples

### 1. Basic Streaming Request
```bash
curl -X POST "http://localhost:8000/execute-ugc-stream" \
  -H "Content-Type: application/json" \
  -d '{
    "character_choice": "2",
    "prebuild_character_choice": 1,
    "product_url": "https://example.com/product.jpg",
    "dialog_choice": "2"
  }'
```

### 2. Custom Character with Custom Dialog
```bash
curl -X POST "http://localhost:8000/execute-ugc-stream" \
  -H "Content-Type: application/json" \
  -d '{
    "character_choice": "1",
    "custom_character_url": "https://example.com/character.jpg",
    "product_url": "https://example.com/product.jpg", 
    "dialog_choice": "1",
    "custom_dialog": "Check out this amazing product!"
  }'
```

### 3. JavaScript EventSource Integration
```javascript
const eventSource = new EventSource('http://localhost:8000/execute-ugc-stream');

eventSource.addEventListener('message', function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'plan_started':
            console.log('Plan started:', data.plan_id);
            break;
        case 'step_output':
            console.log('Step completed:', data.step_name);
            updateProgress(data.step_name, data.output);
            break;
        case 'clarification_needed':
            handleClarification(data.clarifications);
            break;
        case 'video_ready':
            displayVideo(data.video_url);
            break;
        case 'error':
            handleError(data.message);
            break;
    }
});
```

### 4. Clarification Resolution
```javascript
async function resolveClarification(planRunId, clarificationId, response) {
    const result = await fetch(`/resolve-clarification/${planRunId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            clarification_id: clarificationId,
            response: response
        })
    });
    return result.json();
}
```

## Testing Guide

### Prerequisites
1. **Environment Setup**:
   ```bash
   pip install fastapi uvicorn
   export OPENAI_API_KEY="your-key-here"
   ```

2. **Start Server**:
   ```bash
   python api_server.py
   # Server runs on http://localhost:8000
   ```

### Test Sequence

#### 1. Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "UGC Generator API"}
```

#### 2. Get Prebuild Characters
```bash
curl http://localhost:8000/prebuild-characters
# Expected: List of available characters with URLs
```

#### 3. Test Synchronous Execution
```bash
curl -X POST "http://localhost:8000/execute-ugc" \
  -H "Content-Type: application/json" \
  -d '{
    "character_choice": "2",
    "prebuild_character_choice": 1,
    "product_url": "https://example.com/product.jpg",
    "dialog_choice": "2"
  }'
```

#### 4. Test Basic Streaming
```bash
curl -X POST "http://localhost:8000/execute-ugc-stream" \
  -H "Content-Type: application/json" \
  -d '{
    "character_choice": "2", 
    "prebuild_character_choice": 1,
    "product_url": "https://example.com/product.jpg",
    "dialog_choice": "2"
  }'
```

#### 5. Test Real-time Streaming
```bash
curl -X POST "http://localhost:8000/execute-ugc-realtime" \
  -H "Content-Type: application/json" \
  -d '{
    "character_choice": "2",
    "prebuild_character_choice": 1, 
    "product_url": "https://example.com/product.jpg",
    "dialog_choice": "2"
  }'
```

### Expected Streaming Flow
1. `{"type": "plan_started"}` - Initial confirmation
2. `{"type": "step_output"}` - For each completed step
3. `{"type": "completed"}` - Plan execution finished
4. `{"type": "polling_started"}` - Video generation polling begins
5. `{"type": "video_ready"}` - Final video URL available

### Error Testing
- **Invalid URLs**: Test with malformed URLs
- **Missing fields**: Test with incomplete requests
- **Network issues**: Test with unreachable URLs
- **Invalid choices**: Test with out-of-range character selections

## Technical Details

### Dependencies
- **FastAPI**: Web framework with async support
- **Pydantic**: Request/response validation
- **Portia**: AI workflow orchestration
- **asyncio**: Asynchronous programming
- **threading**: Background execution
- **queue**: Thread-safe communication

### Performance Considerations
- **Memory Usage**: Global storage for active plans (should implement cleanup)
- **Concurrent Users**: Thread-per-request for real-time streaming
- **Network Load**: SSE maintains open connections
- **Polling Frequency**: 0.5s for basic streaming, 0.1s for real-time

### Security Considerations
- **Input Validation**: All inputs validated via Pydantic models
- **URL Safety**: Basic URL format validation (could be enhanced)
- **CORS**: Currently allows all origins (should be restricted in production)
- **Rate Limiting**: Not implemented (should be added for production)

### Production Recommendations
1. **Add rate limiting** for API endpoints
2. **Implement authentication** for sensitive operations
3. **Add request logging** for audit trails
4. **Set up monitoring** for system health
5. **Configure proper CORS** policies
6. **Add database persistence** for plan run history
7. **Implement cleanup jobs** for stale plan runs
8. **Add metrics collection** for performance monitoring

### Scalability Notes
- **Horizontal Scaling**: Each instance maintains its own plan storage
- **Load Balancing**: Sticky sessions required for streaming endpoints
- **Database Integration**: Consider Redis for shared plan storage
- **Microservices**: Could split into plan execution and streaming services

## Conclusion

This implementation provides a comprehensive API wrapper for the UGC Generator with full streaming capabilities, proper clarification handling, and production-ready error handling. The system maintains all original functionality while adding modern web API features and real-time streaming capabilities.

The multiple execution modes allow for different client requirements:
- **Synchronous** for simple integration
- **Basic streaming** for progress updates
- **Real-time streaming** for interactive experiences

The clarification handling system enables complex workflows that require human input while maintaining the streaming experience for end users.