from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional, List
import os
from dotenv import load_dotenv
from uuid import UUID
import threading
import queue
import time
import traceback
import concurrent.futures

# Import from main.py
from main import (
    plan,
    portia,
    prebuild_character_urls,
    validate_url,
    get_character_url,
    poll_prediction_until_complete,
    extract_id_and_status,
    UGC_Prediction,
    PredictionStatus,
    PRODUCT_DESCRIPTION_SYSTEM_PROMPT,
    DIALOG_GENERATION_SYSTEM_PROMPT,
    generate_product_ad,
)
from portia import (
    PlanRunState,
    ExecutionHooks,
    MultipleChoiceClarification,
    InputClarification,
)
from portia.execution_hooks import ExecutionHooks as BaseExecutionHooks

# Import from social_scheduler.py
from social_scheduler import (
    ChannelDetection,
    CaptionGeneration,
    SchedulingData,
    ContentValidationTool,
    TimeSchedulingTool,
    ContentRevisionTool,
    social_scheduler_plan,
    create_content_validation_plan,
    create_time_scheduling_plan,
    create_sheets_integration_plan,
    convert_natural_time_to_iso,
)
from utils.config import get_portia_with_custom_tools

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="UGC Generator API", version="1.0.0")


# Custom JSON encoder to handle UUID objects
def json_encoder(obj):
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def safe_json_dumps(data):
    return json.dumps(data, default=json_encoder)


# Global storage for running plan runs and their clarifications
running_plans = {}
plan_clarifications = {}


# Request models
class UGCGeneratorRequest(BaseModel):
    character_choice: str  # "1" for custom, "2" for prebuild
    custom_character_url: Optional[str] = ""
    prebuild_character_choice: Optional[int] = 0
    product_url: str
    dialog_choice: str  # "1" for custom, "2" for auto generate
    custom_dialog: Optional[str] = ""
    system_prompt: Optional[str] = PRODUCT_DESCRIPTION_SYSTEM_PROMPT
    dialog_system_prompt: Optional[str] = DIALOG_GENERATION_SYSTEM_PROMPT


class ClarificationResponse(BaseModel):
    clarification_id: str
    response: str


# Product Ads Request Models
class ProductAdRequest(BaseModel):
    product_url: str  # Product image URL
    ad_prompt: str  # Custom prompt for the product ad


# Social Scheduler Request Models
class SocialSchedulerRequest(BaseModel):
    user_prompt: str  # e.g., "Post this to Instagram tomorrow at 3pm"
    media_url: str  # Video URL from UGC generation
    product_description: str  # Product description from UGC
    dialog: str  # Dialog text from UGC


class SocialClarificationResponse(BaseModel):
    plan_run_id: str
    clarification_argument: str
    response: str


# Response models
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


# Social Scheduler Response Models
class SocialSchedulerResponse(BaseModel):
    plan_id: str
    plan_run_id: str
    state: str
    steps: List[StepOutput]
    final_scheduling_data: Optional[SchedulingData] = None
    generated_captions: Optional[CaptionGeneration] = None
    scheduling_complete: bool = False


def validate_ugc_request(request: UGCGeneratorRequest):
    """Validate UGC Generator request"""
    # Validate character choice
    if request.character_choice == "1":
        if not request.custom_character_url or not validate_url(
            request.custom_character_url
        ):
            raise ValueError("Invalid custom character URL provided")
    elif request.character_choice == "2":
        if not request.prebuild_character_choice or not (
            1 <= request.prebuild_character_choice <= len(prebuild_character_urls)
        ):
            raise ValueError("Invalid prebuild character choice")
    else:
        raise ValueError("Invalid character choice")

    # Validate product URL
    if not validate_url(request.product_url):
        raise ValueError("Invalid product URL")

    # Validate dialog choice
    if request.dialog_choice == "1":
        if not request.custom_dialog or len(request.custom_dialog.strip()) == 0:
            raise ValueError("Custom dialog cannot be empty")
    elif request.dialog_choice != "2":
        raise ValueError("Invalid dialog choice")


def validate_product_ad_request(request: ProductAdRequest):
    """Validate Product Ad request"""
    # Validate product URL
    if not validate_url(request.product_url):
        raise ValueError("Invalid product URL")

    # Validate ad prompt
    if not request.ad_prompt or len(request.ad_prompt.strip()) == 0:
        raise ValueError("Ad prompt cannot be empty")


async def stream_ugc_execution(
    request: UGCGeneratorRequest,
) -> AsyncGenerator[str, None]:
    """Stream UGC Generator execution steps in real-time"""
    plan_run_id = None
    try:
        logger.info(
            f"Starting UGC streaming execution for request: {request.model_dump()}"
        )

        # Validate request
        validate_ugc_request(request)

        # Prepare inputs for the plan
        plan_inputs = {
            "character_choice": request.character_choice,
            "custom_character_url": request.custom_character_url,
            "prebuild_character_choice": request.prebuild_character_choice,
            "product_url": request.product_url,
            "dialog_choice": request.dialog_choice,
            "custom_dialog": request.custom_dialog,
            "system_prompt": request.system_prompt,
            "dialog_system_prompt": request.dialog_system_prompt,
        }

        # Run Portia execution in a separate thread to avoid event loop conflicts
        plan_run = None
        plan_run_id = None
        execution_error = None
        execution_completed = False

        def run_portia():
            nonlocal plan_run, execution_error, execution_completed
            try:
                logger.info("Starting plan execution in separate thread")
                plan_run = portia.run_plan(plan, plan_run_inputs=plan_inputs)
                execution_completed = True
            except Exception as e:
                execution_error = e
                execution_completed = True

        # Start execution in background thread
        execution_thread = threading.Thread(target=run_portia)
        execution_thread.start()

        # Wait for plan to start
        while plan_run is None and execution_error is None:
            await asyncio.sleep(0.1)

        if execution_error:
            raise execution_error

        # Send initial plan information
        plan_id = str(plan_run.plan_id)
        plan_run_id = str(plan_run.id)
        logger.info(f"Plan started - ID: {plan_id}, Run ID: {plan_run_id}")

        # Store the plan run for clarification handling
        running_plans[plan_run_id] = plan_run

        yield f"data: {safe_json_dumps({'type': 'plan_started', 'plan_id': plan_id, 'plan_run_id': plan_run_id})}\n\n"

        # Stream execution steps
        while not execution_completed:
            if plan_run.state == PlanRunState.NEED_CLARIFICATION:
                logger.info(f"Plan {plan_run_id} needs clarification")
                try:
                    clarifications = plan_run.get_outstanding_clarifications()
                    clarification_data = []

                    for clarification in clarifications:
                        clar_info = {
                            "id": str(clarification.id),
                            "category": str(clarification.category),
                            "user_guidance": clarification.user_guidance,
                        }

                        # Add additional fields based on clarification type
                        if hasattr(clarification, "argument_name"):
                            clar_info["argument_name"] = clarification.argument_name
                        if hasattr(clarification, "options"):
                            clar_info["options"] = clarification.options

                        clarification_data.append(clar_info)

                        # Store clarification for later resolution
                        plan_clarifications[str(clarification.id)] = {
                            "clarification": clarification,
                            "plan_run": plan_run,
                        }

                    yield f"data: {safe_json_dumps({'type': 'clarification_needed', 'plan_run_id': plan_run_id, 'clarifications': clarification_data})}\n\n"
                except Exception as e:
                    logger.error(
                        f"Error handling clarifications for plan {plan_run_id}: {str(e)}"
                    )
                    yield f"data: {safe_json_dumps({'type': 'clarification_error', 'plan_run_id': plan_run_id, 'error': str(e)})}\n\n"
                break

            elif plan_run and plan_run.state == PlanRunState.IN_PROGRESS:
                # Stream step outputs
                try:
                    step_outputs = getattr(plan_run.outputs, "step_outputs", {})
                    for key, value in step_outputs.items():
                        # Extract the actual output value
                        output_value = ""
                        if hasattr(value, "value"):
                            output_value = str(value.value)
                        elif hasattr(value, "summary"):
                            output_value = str(value.summary)
                        else:
                            output_value = str(value)

                        step_data = {
                            "type": "step_output",
                            "plan_run_id": plan_run_id,
                            "step_name": key,
                            "output": output_value,
                            "status": "completed",
                        }
                        yield f"data: {safe_json_dumps(step_data)}\n\n"

                except Exception as step_error:
                    yield f"data: {safe_json_dumps({'type': 'step_error', 'plan_run_id': plan_run_id, 'error': str(step_error)})}\n\n"

            # Wait a bit before checking again
            await asyncio.sleep(0.5)

        # Wait for thread completion
        execution_thread.join(timeout=5)

        # Handle completion or failure
        if plan_run and plan_run.state == PlanRunState.COMPLETE:
            final_output = (
                plan_run.outputs.final_output.value
                if hasattr(plan_run.outputs, "final_output")
                and plan_run.outputs.final_output
                else None
            )

            # Extract prediction info for polling
            prediction_id = None
            if final_output:
                if hasattr(final_output, "id"):
                    prediction_id = final_output.id
                elif isinstance(final_output, dict):
                    prediction_id = final_output.get("id")

            completion_data = {
                "type": "completed",
                "plan_run_id": plan_run_id,
                "final_output": (
                    final_output.model_dump()
                    if hasattr(final_output, "model_dump")
                    else final_output
                ),
                "prediction_id": prediction_id,
            }
            yield f"data: {safe_json_dumps(completion_data)}\n\n"

            # If we have a prediction ID, start polling for the final video
            if prediction_id:
                yield f"data: {safe_json_dumps({'type': 'polling_started', 'prediction_id': prediction_id, 'plan_run_id': plan_run_id})}\n\n"

                # Poll for the final video result in a separate thread
                video_result = None
                polling_error = None
                polling_completed = False

                def poll_video():
                    nonlocal video_result, polling_error, polling_completed
                    try:
                        video_result = poll_prediction_until_complete(
                            portia, prediction_id
                        )
                        polling_completed = True
                    except Exception as e:
                        polling_error = e
                        polling_completed = True

                # Start polling in background thread
                polling_thread = threading.Thread(target=poll_video)
                polling_thread.start()

                # Wait for polling completion with periodic status updates
                while not polling_completed:
                    await asyncio.sleep(2)  # Check every 2 seconds
                    yield f"data: {safe_json_dumps({'type': 'polling_update', 'prediction_id': prediction_id, 'message': 'Still polling for video completion...'})}\n\n"

                # Wait for thread to complete
                polling_thread.join(timeout=10)

                if polling_error:
                    yield f"data: {safe_json_dumps({'type': 'video_failed', 'plan_run_id': plan_run_id, 'message': f'Polling error: {str(polling_error)}'})}\n\n"
                elif video_result:
                    # Extract video URL
                    video_url = None
                    if isinstance(video_result, list) and len(video_result) > 0:
                        result_item = video_result[0]
                        if isinstance(result_item, dict) and "output" in result_item:
                            video_url = result_item["output"]

                    yield f"data: {safe_json_dumps({'type': 'video_ready', 'plan_run_id': plan_run_id, 'video_url': video_url, 'full_result': video_result})}\n\n"
                else:
                    yield f"data: {safe_json_dumps({'type': 'video_failed', 'plan_run_id': plan_run_id, 'message': 'Video generation failed or timed out'})}\n\n"

        elif plan_run and plan_run.state == PlanRunState.FAILED:
            yield f"data: {safe_json_dumps({'type': 'error', 'plan_run_id': plan_run_id, 'message': 'Plan execution failed'})}\n\n"
        elif execution_error:
            yield f"data: {safe_json_dumps({'type': 'error', 'plan_run_id': plan_run_id, 'message': f'Execution error: {str(execution_error)}'})}\n\n"

        # Cleanup
        if plan_run_id and plan_run_id in running_plans:
            del running_plans[plan_run_id]
            logger.info(f"Cleaned up plan run {plan_run_id}")

    except Exception as e:
        logger.error(
            f"Error in stream_ugc_execution: {str(e)}\n{traceback.format_exc()}"
        )
        yield f"data: {safe_json_dumps({'type': 'error', 'plan_run_id': plan_run_id, 'message': str(e)})}\n\n"


@app.post("/execute-ugc", response_model=UGCGeneratorResponse)
async def execute_ugc(request: UGCGeneratorRequest):
    """Execute UGC generation and return the complete result"""
    try:
        logger.info(
            f"Starting synchronous UGC execution for request: {request.model_dump()}"
        )

        # Validate request
        validate_ugc_request(request)

        # Prepare inputs for the plan
        plan_inputs = {
            "character_choice": request.character_choice,
            "custom_character_url": request.custom_character_url,
            "prebuild_character_choice": request.prebuild_character_choice,
            "product_url": request.product_url,
            "dialog_choice": request.dialog_choice,
            "custom_dialog": request.custom_dialog,
            "system_prompt": request.system_prompt,
            "dialog_system_prompt": request.dialog_system_prompt,
        }

        # Run the plan in a separate thread to avoid event loop conflicts
        plan_run = None
        execution_error = None
        execution_completed = False

        def run_portia_sync():
            nonlocal plan_run, execution_error, execution_completed
            try:
                logger.info("Executing plan synchronously in separate thread")
                plan_run = portia.run_plan(plan, plan_run_inputs=plan_inputs)
                execution_completed = True
            except Exception as e:
                execution_error = e
                execution_completed = True

        # Start execution in background thread
        execution_thread = threading.Thread(target=run_portia_sync)
        execution_thread.start()

        # Wait for completion
        execution_thread.join()

        if execution_error:
            raise execution_error

        logger.info(f"Plan execution completed with state: {plan_run.state}")

        # Build response with all steps
        steps = []
        step_outputs = (
            plan_run.outputs.step_outputs
            if hasattr(plan_run.outputs, "step_outputs")
            else {}
        )

        for i, (key, value) in enumerate(step_outputs.items()):
            # Extract the actual output value
            output_value = ""
            if hasattr(value, "value"):
                output_value = str(value.value)
            elif hasattr(value, "summary"):
                output_value = str(value.summary)
            else:
                output_value = str(value)

            steps.append(
                StepOutput(
                    step_index=i,
                    step_name=key,
                    output=output_value,
                    status="completed",
                )
            )

        final_output = (
            plan_run.outputs.final_output.value
            if hasattr(plan_run.outputs, "final_output")
            and plan_run.outputs.final_output
            else None
        )

        # Get prediction ID for video polling
        prediction_id = None
        video_url = None

        if final_output:
            if hasattr(final_output, "id"):
                prediction_id = final_output.id
            elif isinstance(final_output, dict):
                prediction_id = final_output.get("id")

            # Poll for final video if prediction ID exists
            if prediction_id:
                logger.info(
                    f"Polling for video completion with prediction ID: {prediction_id}"
                )

                # Poll in separate thread to avoid event loop conflicts
                def poll_video_sync():
                    return poll_prediction_until_complete(portia, prediction_id)

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(poll_video_sync)
                    final_video_result = future.result(timeout=120)  # 2 minute timeout

                if (
                    final_video_result
                    and isinstance(final_video_result, list)
                    and len(final_video_result) > 0
                ):
                    result_item = final_video_result[0]
                    if isinstance(result_item, dict) and "output" in result_item:
                        video_url = result_item["output"]
                        logger.info(
                            f"Video generation completed successfully: {video_url}"
                        )
                    else:
                        logger.warning(
                            "Video result format unexpected - no output field found"
                        )
                else:
                    logger.warning(
                        "Video generation failed or returned unexpected format"
                    )

        return UGCGeneratorResponse(
            plan_id=str(plan_run.plan_id),
            plan_run_id=str(plan_run.id),
            state=str(plan_run.state),
            steps=steps,
            final_output=final_output,
            video_url=video_url,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute-ugc-stream")
async def execute_ugc_stream(request: UGCGeneratorRequest):
    """Execute UGC generation with streaming response using Server-Sent Events (SSE)"""
    return StreamingResponse(
        stream_ugc_execution(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@app.post("/resolve-clarification/{plan_run_id}")
async def resolve_clarification(
    plan_run_id: str, clarification_response: ClarificationResponse
):
    """Resolve a clarification and resume plan execution"""
    try:
        clarification_id = clarification_response.clarification_id

        if clarification_id not in plan_clarifications:
            raise HTTPException(
                status_code=404, detail=f"Clarification {clarification_id} not found"
            )

        clarification_data = plan_clarifications[clarification_id]
        clarification = clarification_data["clarification"]
        plan_run = clarification_data["plan_run"]

        def resolve_and_resume():
            # Resolve the clarification
            updated_plan_run = portia.resolve_clarification(
                clarification, clarification_response.response, plan_run
            )

            # Resume the plan run
            resumed_plan_run = portia.resume(updated_plan_run)
            return resumed_plan_run

        # Run in separate thread to avoid event loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(resolve_and_resume)
            resumed_plan_run = future.result()

        # Update stored plan run
        running_plans[plan_run_id] = resumed_plan_run

        # Clean up the clarification
        del plan_clarifications[clarification_id]

        return {
            "status": "resolved",
            "plan_run_id": plan_run_id,
            "clarification_id": clarification_id,
            "new_state": str(resumed_plan_run.state),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/plan-status/{plan_run_id}")
async def get_plan_status(plan_run_id: str):
    """Get the current status of a running plan"""
    if plan_run_id not in running_plans:
        raise HTTPException(status_code=404, detail=f"Plan run {plan_run_id} not found")

    plan_run = running_plans[plan_run_id]

    return {
        "plan_run_id": plan_run_id,
        "state": str(plan_run.state),
        "current_step_index": getattr(plan_run, "current_step_index", 0),
        "has_clarifications": len(plan_run.get_outstanding_clarifications()) > 0,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "UGC Generator API"}


@app.post("/execute-ugc-realtime")
async def execute_ugc_realtime(request: UGCGeneratorRequest):
    """TRUE REAL-TIME streaming endpoint using Portia execution hooks"""

    async def generate():
        try:
            # Validate request
            validate_ugc_request(request)

            # Send initial data
            yield f"data: {safe_json_dumps({'type': 'started', 'message': 'Starting real-time UGC generation...'})}\n\n"

            # Prepare inputs for the plan
            plan_inputs = {
                "character_choice": request.character_choice,
                "custom_character_url": request.custom_character_url,
                "prebuild_character_choice": request.prebuild_character_choice,
                "product_url": request.product_url,
                "dialog_choice": request.dialog_choice,
                "custom_dialog": request.custom_dialog,
                "system_prompt": request.system_prompt,
                "dialog_system_prompt": request.dialog_system_prompt,
            }

            # Create event queue for this execution
            event_queue = queue.Queue()

            # Define streaming hook functions
            def before_step_hook(plan, plan_run, step):
                logger.info(f"Hook: Before step - {getattr(step, 'task', 'Unknown')}")
                event_queue.put(
                    {
                        "type": "step_started",
                        "step_index": getattr(plan_run, "current_step_index", 0),
                        "step_name": getattr(step, "task", "Unknown Step"),
                        "tool_id": getattr(step, "tool_id", "unknown"),
                        "message": f"Starting step: {getattr(step, 'task', 'Unknown Step')}",
                        "plan_run_id": str(plan_run.id),
                    }
                )

            def after_step_hook(plan, plan_run, step, output):
                logger.info(f"Hook: After step - {getattr(step, 'task', 'Unknown')}")
                # Get the step output
                output_value = ""
                if hasattr(output, "value"):
                    output_value = str(output.value)[:200]  # Truncate long outputs
                elif hasattr(output, "summary"):
                    output_value = str(output.summary)[:200]
                else:
                    output_value = str(output)[:200]

                event_queue.put(
                    {
                        "type": "step_completed",
                        "step_index": getattr(plan_run, "current_step_index", 0),
                        "step_name": getattr(step, "task", "Unknown Step"),
                        "tool_id": getattr(step, "tool_id", "unknown"),
                        "output": output_value,
                        "message": f"Completed step: {getattr(step, 'task', 'Unknown Step')}",
                        "plan_run_id": str(plan_run.id),
                    }
                )

            # Run Portia in a separate thread with streaming hooks
            plan_run_result = None
            execution_error = None
            execution_completed = False

            def run_portia():
                nonlocal plan_run_result, execution_error, execution_completed
                try:
                    logger.info("Starting plan execution with custom hooks")

                    # Temporarily modify the portia instance's execution hooks
                    original_hooks = portia.execution_hooks

                    # Create new hooks that include our event capturing
                    custom_hooks = BaseExecutionHooks(
                        before_step_execution=before_step_hook,
                        after_step_execution=after_step_hook,
                    )

                    # Set the custom hooks
                    portia.execution_hooks = custom_hooks

                    try:
                        # Run the plan with our custom hooks
                        plan_run_result = portia.run_plan(
                            plan, plan_run_inputs=plan_inputs
                        )
                        logger.info(
                            f"Plan execution completed with state: {plan_run_result.state}"
                        )
                    finally:
                        # Restore original hooks
                        portia.execution_hooks = original_hooks

                    # Handle clarifications
                    while plan_run_result.state == PlanRunState.NEED_CLARIFICATION:
                        clarifications = (
                            plan_run_result.get_outstanding_clarifications()
                        )
                        for clarification in clarifications:
                            event_queue.put(
                                {
                                    "type": "clarification_needed",
                                    "clarification_id": str(clarification.id),
                                    "user_guidance": clarification.user_guidance,
                                    "plan_run_id": str(plan_run_result.id),
                                    "message": "Clarification needed - execution paused",
                                }
                            )
                        break

                    if plan_run_result.state == PlanRunState.COMPLETE:
                        # Extract final output and prediction ID
                        final_output = (
                            plan_run_result.outputs.final_output.value
                            if hasattr(plan_run_result.outputs, "final_output")
                            and plan_run_result.outputs.final_output
                            else None
                        )

                        prediction_id = None
                        if final_output:
                            if hasattr(final_output, "id"):
                                prediction_id = final_output.id
                            elif isinstance(final_output, dict):
                                prediction_id = final_output.get("id")

                        event_queue.put(
                            {
                                "type": "plan_completed",
                                "message": "UGC plan completed successfully",
                                "plan_run_id": str(plan_run_result.id),
                                "prediction_id": prediction_id,
                            }
                        )

                        # Poll for final video if prediction ID exists
                        if prediction_id:
                            event_queue.put(
                                {
                                    "type": "video_polling_started",
                                    "prediction_id": prediction_id,
                                    "message": "Polling for video generation completion...",
                                }
                            )

                            # Since we're already in a separate thread, we can safely poll
                            try:
                                logger.info(
                                    f"Starting video polling for prediction: {prediction_id}"
                                )
                                final_video_result = poll_prediction_until_complete(
                                    portia, prediction_id
                                )

                                if final_video_result:
                                    video_url = None
                                    if (
                                        isinstance(final_video_result, list)
                                        and len(final_video_result) > 0
                                    ):
                                        result_item = final_video_result[0]
                                        if (
                                            isinstance(result_item, dict)
                                            and "output" in result_item
                                        ):
                                            video_url = result_item["output"]

                                    event_queue.put(
                                        {
                                            "type": "video_completed",
                                            "video_url": video_url,
                                            "full_result": final_video_result,
                                            "message": "Video generation completed!",
                                        }
                                    )
                                    logger.info(
                                        f"Video polling completed successfully: {video_url}"
                                    )
                                else:
                                    event_queue.put(
                                        {
                                            "type": "video_failed",
                                            "message": "Video generation failed or timed out",
                                        }
                                    )
                                    logger.warning("Video polling failed or timed out")
                            except Exception as poll_error:
                                logger.error(f"Video polling error: {poll_error}")
                                event_queue.put(
                                    {
                                        "type": "video_failed",
                                        "message": f"Video polling error: {str(poll_error)}",
                                    }
                                )

                    execution_completed = True

                except Exception as e:
                    logger.error(
                        f"Error in run_portia thread: {str(e)}\n{traceback.format_exc()}"
                    )
                    execution_error = e
                    execution_completed = True

            # Start execution in background thread
            execution_thread = threading.Thread(target=run_portia)
            execution_thread.start()

            # Stream events in real-time as they come from the hooks
            logger.info("Starting real-time event streaming loop")
            while not execution_completed:
                # Get new events from the event queue
                events = []
                while not event_queue.empty():
                    try:
                        events.append(event_queue.get_nowait())
                    except queue.Empty:
                        break

                # Stream each event immediately as it arrives
                for event in events:
                    logger.debug(f"Streaming event: {event['type']}")
                    yield f"data: {safe_json_dumps(event)}\n\n"

                # Check for execution error
                if execution_error:
                    logger.error(f"Streaming execution error: {execution_error}")
                    yield f"data: {safe_json_dumps({'type': 'error', 'message': str(execution_error)})}\n\n"
                    break

                # Small delay to avoid busy waiting
                await asyncio.sleep(0.1)

            logger.info(
                f"Real-time streaming completed. execution_completed={execution_completed}, execution_error={execution_error}"
            )

            # Wait for thread to complete
            execution_thread.join(timeout=2)

            # Send any remaining events
            final_events = []
            while not event_queue.empty():
                try:
                    final_events.append(event_queue.get_nowait())
                except queue.Empty:
                    break

            for event in final_events:
                yield f"data: {safe_json_dumps(event)}\n\n"

        except Exception as e:
            yield f"data: {safe_json_dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/prebuild-characters")
async def get_prebuild_characters():
    """Get list of available prebuild character URLs"""
    return {
        "characters": [
            {"index": i + 1, "url": url}
            for i, url in enumerate(prebuild_character_urls)
        ]
    }


# Product Ads Endpoints
@app.post("/execute-product-ad")
async def execute_product_ad(request: ProductAdRequest):
    """Execute Product Ad generation and return the complete result"""
    try:
        logger.info(
            f"Starting Product Ad execution for request: {request.model_dump()}"
        )

        # Validate request
        validate_product_ad_request(request)

        # Run the Product Ad generation in a separate thread to avoid event loop conflicts
        result = None
        execution_error = None

        def run_product_ad_sync():
            nonlocal result, execution_error
            try:
                logger.info("Executing Product Ad generation in separate thread")
                result = generate_product_ad()  # This will use the input prompts

                # For API integration, we need to modify generate_product_ad to accept parameters
                # For now, let's create a wrapper that calls the function with the provided parameters
                from portia import PlanBuilderV2, Input

                # Create product ad generation plan (similar to main.py)
                product_ad_plan = (
                    PlanBuilderV2("Product Ad Generator")
                    .input(name="product_url", description="Product image URL")
                    .input(name="ad_prompt", description="Ad prompt from user")
                    .single_tool_agent_step(
                        tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
                        task="""
                        Call the Replicate tool with this EXACT structure:
                        {
                          "version": "7428dcc4cdb6d758301c2ae57ca01279e9b6899c5cb01f18f4d577c412b14390",
                          "input": {
                            "prompt": [use the ad_prompt input],
                            "lighting": "auto",
                            "audio_mode": "off",
                            "image_style": "studio",
                            "camera_movement": "auto",
                            "reference_image": [use the product_url input]
                          },
                          "jq_filter": "{id: .id, status: .status}",
                          "Prefer": "wait=1"
                        }
                        
                        DO NOT OMIT THE "version" FIELD. It is required.
                        Return ONLY the id and status from the response.
                        """,
                        inputs=[Input("product_url"), Input("ad_prompt")],
                        step_name="generate_product_ad",
                    )
                    .final_output()
                    .build()
                )

                # Run the product ad plan
                plan_inputs = {
                    "product_url": request.product_url,
                    "ad_prompt": request.ad_prompt,
                }

                plan_run = portia.run_plan(product_ad_plan, plan_run_inputs=plan_inputs)

                # Extract prediction ID and status
                final_output = plan_run.outputs.final_output.value
                prediction_id, prediction_status = extract_id_and_status(final_output)

                if prediction_id:
                    logger.info(
                        f"Product Ad generation started with prediction ID: {prediction_id}"
                    )

                    # Poll for completion
                    final_result = poll_prediction_until_complete(portia, prediction_id)

                    if final_result:
                        # Extract video URL
                        video_url = None
                        if isinstance(final_result, list) and len(final_result) > 0:
                            result_item = final_result[0]
                            if (
                                isinstance(result_item, dict)
                                and "output" in result_item
                            ):
                                video_url = result_item["output"]

                        result = {
                            "prediction_id": prediction_id,
                            "status": "completed",
                            "video_url": video_url,
                            "full_result": final_result,
                            "product_url": request.product_url,
                            "ad_prompt": request.ad_prompt,
                        }
                    else:
                        result = {
                            "prediction_id": prediction_id,
                            "status": "failed",
                            "error": "Video generation failed or timed out",
                            "product_url": request.product_url,
                            "ad_prompt": request.ad_prompt,
                        }
                else:
                    result = {
                        "status": "failed",
                        "error": "Could not extract prediction ID",
                        "product_url": request.product_url,
                        "ad_prompt": request.ad_prompt,
                    }

            except Exception as e:
                execution_error = e

        # Start execution in background thread
        execution_thread = threading.Thread(target=run_product_ad_sync)
        execution_thread.start()

        # Wait for completion
        execution_thread.join()

        if execution_error:
            raise execution_error

        logger.info(f"Product Ad execution completed: {result}")

        return result

    except Exception as e:
        logger.error(f"Error in Product Ad execution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Social Scheduler Endpoints
@app.post("/execute-social-scheduler", response_model=SocialSchedulerResponse)
async def execute_social_scheduler(request: SocialSchedulerRequest):
    """Execute social scheduler workflow with clarification handling"""
    try:
        logger.info(
            f"Starting social scheduler execution for request: {request.model_dump()}"
        )

        # Get Portia instance with custom tools
        social_portia = get_portia_with_custom_tools()

        # Step 1: Generate initial captions
        # Use ThreadPoolExecutor to avoid event loop conflicts
        caption_run = None
        with concurrent.futures.ThreadPoolExecutor() as executor:

            def run_social_plan():
                return social_portia.run_plan(
                    social_scheduler_plan,
                    plan_run_inputs={
                        "user_prompt": request.user_prompt,
                        "media_url": request.media_url,
                        "product_description": request.product_description,
                        "dialog": request.dialog,
                    },
                )

            future = executor.submit(run_social_plan)
            caption_run = future.result(timeout=120)  # 2 minute timeout

        generated_captions = caption_run.outputs.final_output.value

        # Store the plan run for clarifications
        plan_run_id = str(caption_run.id)
        running_plans[plan_run_id] = {
            "social_portia": social_portia,
            "generated_captions": generated_captions,
            "request": request,
            "current_phase": "content_validation",
        }

        # Build initial response
        steps = []
        for i, (key, value) in enumerate(caption_run.outputs.step_outputs.items()):
            output_value = value.value if hasattr(value, "value") else str(value)
            steps.append(
                StepOutput(
                    step_index=i,
                    step_name=f"Step {i+1}: {key}",
                    output=output_value,
                    status="completed",
                )
            )

        response = SocialSchedulerResponse(
            plan_id=str(caption_run.plan_id),
            plan_run_id=plan_run_id,
            state=str(caption_run.state),
            steps=steps,
            generated_captions=generated_captions,
            scheduling_complete=False,
        )

        return response

    except Exception as e:
        logger.error(f"Error in social scheduler execution: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute-social-scheduler-realtime")
async def execute_social_scheduler_realtime(request: SocialSchedulerRequest):
    """Execute social scheduler workflow with real-time streaming"""
    return StreamingResponse(
        stream_social_scheduler_execution(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.post("/resume-social-streaming/{plan_run_id}")
async def resume_social_streaming(
    plan_run_id: str, clarification_response: ClarificationResponse
):
    """Resume a streaming social scheduler plan after resolving clarification"""
    try:
        # Find the clarification to resolve
        clarification_id = clarification_response.clarification_id
        if clarification_id not in plan_clarifications:
            raise HTTPException(
                status_code=404, detail=f"Clarification {clarification_id} not found"
            )

        clarification_data = plan_clarifications[clarification_id]
        clarification = clarification_data["clarification"]
        plan_run = clarification_data["plan_run"]
        
        # Get the stored plan data
        if plan_run_id not in running_plans:
            raise HTTPException(status_code=404, detail="Plan run not found")
        
        plan_data = running_plans[plan_run_id]
        social_portia = plan_data["social_portia"]

        def resolve_and_resume():
            # Resolve the clarification
            updated_plan_run = social_portia.resolve_clarification(
                clarification, clarification_response.response, plan_run
            )
            # Resume the plan run
            resumed_plan_run = social_portia.resume(updated_plan_run)
            
            # Check which workflow step we're in
            workflow_step = clarification_data.get("workflow_step", "content_validation")
            
            if workflow_step == "content_validation" and resumed_plan_run.state == PlanRunState.COMPLETE:
                # Content validation completed, continue to time scheduling
                logger.info("Content validation completed, proceeding to time scheduling")
                
                from social_scheduler import create_time_scheduling_plan
                
                time_plan = create_time_scheduling_plan()
                time_run = social_portia.run_plan(time_plan)
                
                if time_run.state == PlanRunState.NEED_CLARIFICATION:
                    # Store time scheduling clarification
                    time_clarifications = time_run.get_outstanding_clarifications()
                    for time_clarification in time_clarifications:
                        plan_clarifications[str(time_clarification.id)] = {
                            "clarification": time_clarification,
                            "plan_run": time_run,
                            "workflow_step": "time_scheduling",
                            "social_portia": social_portia,
                            "validation_result": resumed_plan_run.outputs.final_output.value,
                            "request": clarification_data["request"]
                        }
                    
                    return time_run
                else:
                    # Time scheduling completed without clarification, continue to sheets
                    return _continue_to_sheets(time_run, clarification_data)
            
            elif workflow_step == "time_scheduling" and resumed_plan_run.state == PlanRunState.COMPLETE:
                # Time scheduling completed, continue to Google Sheets
                logger.info("Time scheduling completed, proceeding to Google Sheets")
                return _continue_to_sheets(resumed_plan_run, clarification_data)
            
            return resumed_plan_run
        
        def _continue_to_sheets(time_run, clarification_data):
            """Helper function to continue to Google Sheets step"""
            from social_scheduler import create_sheets_integration_plan, SchedulingData, convert_natural_time_to_iso
            
            time_result = time_run.outputs.final_output.value
            scheduled_time = convert_natural_time_to_iso(time_result)
            request = clarification_data["request"]
            
            # Get final captions - could be from validation_result or generated_captions
            validation_result = clarification_data.get("validation_result")
            if validation_result and isinstance(validation_result, str):
                # Parse validation result if it's JSON
                try:
                    import json
                    final_captions_data = json.loads(validation_result)
                    from social_scheduler import CaptionGeneration
                    final_captions = CaptionGeneration(**final_captions_data)
                except:
                    final_captions = clarification_data.get("generated_captions")
            else:
                final_captions = clarification_data.get("generated_captions")
            
            # Prepare final data
            final_data = SchedulingData(
                media_url=request.media_url,
                instagram_caption=final_captions.instagram_caption,
                date_time=scheduled_time,
                twitter_post=final_captions.twitter_post or "",
                channel=final_captions.channel,
            )
            
            sheets_plan = create_sheets_integration_plan(final_data)
            sheets_run = clarification_data["social_portia"].run_plan(
                sheets_plan,
                plan_run_inputs={
                    "media_url": final_data.media_url,
                    "instagram_caption": final_data.instagram_caption,
                    "date_time": final_data.date_time,
                    "twitter_post": final_data.twitter_post,
                    "channel": final_data.channel,
                },
            )
            
            return sheets_run

        # Run in separate thread to avoid event loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(resolve_and_resume)
            resumed_plan_run = future.result()

        # Update stored plan run
        plan_data["caption_run"] = resumed_plan_run

        # Clean up the clarification
        del plan_clarifications[clarification_id]

        return {
            "status": "resumed",
            "plan_run_id": plan_run_id,
            "clarification_id": clarification_id,
            "new_state": str(resumed_plan_run.state),
            "message": "Plan execution resumed successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resume-social-plan/{plan_run_id}")
async def resume_social_plan(
    plan_run_id: str, clarification_response: ClarificationResponse
):
    """Resume social scheduler plan after resolving clarification using Portia's built-in system"""
    try:
        if plan_run_id not in running_plans:
            raise HTTPException(status_code=404, detail="Plan run not found")

        plan_data = running_plans[plan_run_id]
        social_portia = plan_data["social_portia"]
        caption_run = plan_data["caption_run"]

        logger.info(
            f"Resuming social plan {plan_run_id} with clarification response: {clarification_response.response}"
        )

        # Find the clarification to resolve
        clarifications = caption_run.get_outstanding_clarifications()
        target_clarification = None

        for clarification in clarifications:
            if str(clarification.id) == clarification_response.clarification_id:
                target_clarification = clarification
                break

        if not target_clarification:
            raise HTTPException(
                status_code=404,
                detail=f"Clarification {clarification_response.clarification_id} not found",
            )

        def resolve_and_resume():
            """Resolve clarification and resume plan execution"""
            # Resolve the clarification with user response
            updated_plan_run = social_portia.resolve_clarification(
                target_clarification, clarification_response.response, caption_run
            )

            # Resume the plan execution
            resumed_plan_run = social_portia.resume(updated_plan_run)
            return resumed_plan_run

        # Execute in separate thread to avoid event loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(resolve_and_resume)
            resumed_plan_run = future.result(timeout=120)

        # Update stored plan run
        plan_data["caption_run"] = resumed_plan_run

        # Check the final state after resumption
        if resumed_plan_run.state == PlanRunState.COMPLETE:
            # Plan completed successfully
            final_captions = resumed_plan_run.outputs.final_output.value
            plan_data["current_phase"] = "completed"
            plan_data["final_captions"] = final_captions

            return {
                "status": "completed",
                "message": "Social scheduler plan completed successfully",
                "plan_run_id": plan_run_id,
                "final_captions": final_captions.model_dump(),
                "state": str(resumed_plan_run.state),
            }

        elif resumed_plan_run.state == PlanRunState.NEED_CLARIFICATION:
            # Plan needs another clarification
            clarifications = resumed_plan_run.get_outstanding_clarifications()
            clarification_data = []

            for clarification in clarifications:
                clarification_info = {
                    "id": str(clarification.id),
                    "category": clarification.category.value,
                    "user_guidance": clarification.user_guidance,
                    "argument_name": getattr(clarification, "argument_name", None),
                    "options": getattr(clarification, "options", None),
                    "resolved": clarification.resolved,
                }
                clarification_data.append(clarification_info)

            return {
                "status": "needs_clarification",
                "message": "Plan execution continues but needs another clarification",
                "plan_run_id": plan_run_id,
                "clarifications": clarification_data,
                "state": str(resumed_plan_run.state),
            }

        else:
            return {
                "status": "unknown",
                "message": f"Plan execution resumed with unexpected state: {resumed_plan_run.state}",
                "plan_run_id": plan_run_id,
                "state": str(resumed_plan_run.state),
            }

    except Exception as e:
        logger.error(f"Error resuming social plan: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/resolve-social-clarification/{plan_run_id}")
async def resolve_social_clarification(
    plan_run_id: str, response: SocialClarificationResponse
):
    """Legacy endpoint - resolve clarification for social scheduler (kept for compatibility)"""
    try:
        if plan_run_id not in running_plans:
            raise HTTPException(status_code=404, detail="Plan run not found")

        plan_data = running_plans[plan_run_id]
        social_portia = plan_data["social_portia"]

        logger.info(
            f"Resolving social clarification for plan {plan_run_id}: {response.clarification_argument} = {response.response}"
        )

        # Handle different phases of the social workflow
        current_phase = plan_data.get("current_phase", "content_validation")

        if current_phase == "content_validation":
            # Continue with content validation workflow
            return await handle_content_validation_clarification(
                plan_run_id, response, plan_data
            )
        elif current_phase == "time_scheduling":
            # Continue with time scheduling workflow
            return await handle_time_scheduling_clarification(
                plan_run_id, response, plan_data
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown workflow phase: {current_phase}"
            )

    except Exception as e:
        logger.error(f"Error resolving social clarification: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def handle_content_validation_clarification(
    plan_run_id: str, response: SocialClarificationResponse, plan_data: dict
):
    """Handle content validation clarifications"""
    social_portia = plan_data["social_portia"]
    generated_captions = plan_data["generated_captions"]

    # Create content validation plan
    validation_plan = create_content_validation_plan(generated_captions)

    # Store clarification response
    if "clarification_responses" not in plan_data:
        plan_data["clarification_responses"] = {}
    plan_data["clarification_responses"][
        response.clarification_argument
    ] = response.response

    # If user approved content, move to time scheduling
    if "approve" in response.response.lower():
        plan_data["current_phase"] = "time_scheduling"
        plan_data["approved_captions"] = generated_captions

        return {
            "status": "content_approved",
            "message": "Content approved, ready for time scheduling",
            "next_phase": "time_scheduling",
        }
    else:
        # User wants changes - continue content validation cycle
        return {
            "status": "content_revision_requested",
            "message": "Content revision requested",
            "next_phase": "content_validation",
        }


async def handle_time_scheduling_clarification(
    plan_run_id: str, response: SocialClarificationResponse, plan_data: dict
):
    """Handle time scheduling clarifications"""
    try:
        # Convert natural language time to ISO format
        scheduled_time = convert_natural_time_to_iso(response.response)

        # Get final captions
        approved_captions = plan_data.get(
            "approved_captions", plan_data["generated_captions"]
        )
        request = plan_data["request"]

        # Create final scheduling data
        final_data = SchedulingData(
            media_url=request.media_url,
            instagram_caption=approved_captions.instagram_caption,
            date_time=scheduled_time,
            twitter_post=approved_captions.twitter_post or "",
            channel=approved_captions.channel,
        )

        # Save to Google Sheets
        social_portia = plan_data["social_portia"]
        sheets_plan = create_sheets_integration_plan(final_data)

        # Use ThreadPoolExecutor to avoid event loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:

            def run_sheets_plan():
                return social_portia.run_plan(
                    sheets_plan,
                    plan_run_inputs={
                        "media_url": final_data.media_url,
                        "instagram_caption": final_data.instagram_caption,
                        "date_time": final_data.date_time,
                        "twitter_post": final_data.twitter_post,
                        "channel": final_data.channel,
                    },
                )

            future = executor.submit(run_sheets_plan)
            sheets_run = future.result(timeout=60)  # 1 minute timeout

        # Mark as completed
        plan_data["current_phase"] = "completed"
        plan_data["final_scheduling_data"] = final_data

        return {
            "status": "scheduling_complete",
            "message": "Social media post has been scheduled successfully!",
            "final_data": final_data.model_dump(),
            "scheduled_time": scheduled_time,
        }

    except Exception as e:
        logger.error(f"Error in time scheduling: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def stream_social_scheduler_execution(
    request: SocialSchedulerRequest,
) -> AsyncGenerator[str, None]:
    """Stream social scheduler execution with real-time updates using execution hooks"""
    try:
        # Send initial data
        yield f"data: {safe_json_dumps({'type': 'started', 'message': 'Starting social scheduler workflow...'})}\n\n"

        # Get Portia instance with custom tools
        social_portia = get_portia_with_custom_tools()

        # Create event queue for this execution
        event_queue = queue.Queue()

        # Define streaming hook functions
        def before_step_hook(plan, plan_run, step):
            logger.info(
                f"Social Hook: Before step - {getattr(step, 'task', 'Unknown')}"
            )
            event_queue.put(
                {
                    "type": "step_started",
                    "step_index": getattr(plan_run, "current_step_index", 0),
                    "step_name": getattr(step, "task", "Unknown Step"),
                    "tool_id": getattr(step, "tool_id", "unknown"),
                    "message": f"Starting step: {getattr(step, 'task', 'Unknown Step')}",
                    "plan_run_id": str(plan_run.id),
                }
            )

        def after_step_hook(plan, plan_run, step, output):
            logger.info(f"Social Hook: After step - {getattr(step, 'task', 'Unknown')}")
            # Get the step output
            output_value = ""
            if hasattr(output, "value"):
                output_value = str(output.value)[:200]  # Truncate long outputs
            elif hasattr(output, "summary"):
                output_value = str(output.summary)[:200]
            else:
                output_value = str(output)[:200]

            event_queue.put(
                {
                    "type": "step_completed",
                    "step_index": getattr(plan_run, "current_step_index", 0),
                    "step_name": getattr(step, "task", "Unknown Step"),
                    "tool_id": getattr(step, "tool_id", "unknown"),
                    "output": output_value,
                    "message": f"Completed step: {getattr(step, 'task', 'Unknown Step')}",
                    "plan_run_id": str(plan_run.id),
                }
            )

        # Run social portia execution in a separate thread with real-time hooks
        plan_run_result = None
        execution_error = None
        execution_completed = False

        def run_social_portia():
            nonlocal plan_run_result, execution_error, execution_completed
            try:
                logger.info(
                    "Starting social scheduler plan execution with custom hooks"
                )

                # Temporarily modify the social_portia instance's execution hooks
                original_hooks = social_portia.execution_hooks

                # Create new hooks that include our event capturing
                custom_hooks = BaseExecutionHooks(
                    before_step_execution=before_step_hook,
                    after_step_execution=after_step_hook,
                )

                # Set the custom hooks
                social_portia.execution_hooks = custom_hooks

                try:
                    # Step 1: Generate captions
                    event_queue.put({
                        "type": "workflow_step",
                        "step": "caption_generation",
                        "message": "Step 1/4: Generating social media captions..."
                    })
                    
                    caption_run = social_portia.run_plan(
                        social_scheduler_plan,
                        plan_run_inputs={
                            "user_prompt": request.user_prompt,
                            "media_url": request.media_url,
                            "product_description": request.product_description,
                            "dialog": request.dialog,
                        },
                    )
                    
                    if caption_run.state != PlanRunState.COMPLETE:
                        raise Exception(f"Caption generation failed with state: {caption_run.state}")
                    
                    generated_captions = caption_run.outputs.final_output.value
                    event_queue.put({
                        "type": "step_result", 
                        "step": "caption_generation",
                        "result": generated_captions.model_dump() if hasattr(generated_captions, 'model_dump') else generated_captions,
                        "message": "Captions generated successfully"
                    })

                    # Step 2: Content validation (with clarifications)
                    from social_scheduler import create_content_validation_plan
                    
                    event_queue.put({
                        "type": "workflow_step",
                        "step": "content_validation", 
                        "message": "Step 2/4: Validating content with user..."
                    })
                    
                    validation_plan = create_content_validation_plan(generated_captions)
                    validation_run = social_portia.run_plan(validation_plan)
                    
                    # Content validation requires clarifications - store and return
                    if validation_run.state == PlanRunState.NEED_CLARIFICATION:
                        plan_run_result = validation_run
                        return
                    
                    # If validation completed without clarifications, continue to next steps
                    # (This would be rare as ContentValidationTool always asks for approval)
                    validation_result = validation_run.outputs.final_output.value
                    plan_run_result = validation_run
                    logger.info(
                        f"Social scheduler plan completed with state: {plan_run_result.state}"
                    )
                finally:
                    # Restore original hooks
                    social_portia.execution_hooks = original_hooks

                # Handle clarifications from content validation
                if plan_run_result.state == PlanRunState.NEED_CLARIFICATION:
                    plan_run_id = str(plan_run_result.id)
                    
                    # Store plan run for clarification handling  
                    running_plans[plan_run_id] = {
                        "social_portia": social_portia,
                        "caption_run": plan_run_result,
                        "request": request,
                        "current_phase": "content_validation",
                        "generated_captions": generated_captions
                    }
                    
                    clarifications = plan_run_result.get_outstanding_clarifications()
                    for clarification in clarifications:
                        event_queue.put(
                            {
                                "type": "clarification_needed",
                                "clarification_id": str(clarification.id),
                                "user_guidance": clarification.user_guidance,
                                "plan_run_id": plan_run_id,
                                "message": "Content validation requires user input",
                                "argument_name": getattr(
                                    clarification, "argument_name", None
                                ),
                                "options": getattr(clarification, "options", None),
                                "category": str(clarification.category),
                                "workflow_step": "content_validation"
                            }
                        )
                        
                        # Store clarification for later resolution
                        plan_clarifications[str(clarification.id)] = {
                            "clarification": clarification,
                            "plan_run": plan_run_result,
                            "workflow_step": "content_validation",
                            "social_portia": social_portia,
                            "generated_captions": generated_captions,
                            "request": request
                        }

                elif plan_run_result.state == PlanRunState.COMPLETE:
                    # Extract final output
                    final_output = (
                        plan_run_result.outputs.final_output.value
                        if hasattr(plan_run_result.outputs, "final_output")
                        and plan_run_result.outputs.final_output
                        else None
                    )

                    event_queue.put(
                        {
                            "type": "plan_completed",
                            "message": "Social scheduler plan completed successfully",
                            "plan_run_id": str(plan_run_result.id),
                            "final_captions": (
                                final_output.model_dump()
                                if final_output and hasattr(final_output, "model_dump")
                                else final_output
                            ),
                        }
                    )

                execution_completed = True

            except Exception as e:
                logger.error(
                    f"Error in run_social_portia thread: {str(e)}\\n{traceback.format_exc()}"
                )
                execution_error = e
                execution_completed = True

        # Start execution in background thread
        execution_thread = threading.Thread(target=run_social_portia)
        execution_thread.start()

        # Stream events in real-time as they come from the hooks
        logger.info("Starting real-time social scheduler event streaming loop")
        while not execution_completed:
            # Get new events from the event queue
            events = []
            while not event_queue.empty():
                try:
                    events.append(event_queue.get_nowait())
                except queue.Empty:
                    break

            # Stream each event immediately as it arrives
            for event in events:
                logger.debug(f"Streaming social event: {event['type']}")
                yield f"data: {safe_json_dumps(event)}\n\n"

            # Check for execution error
            if execution_error:
                logger.error(f"Streaming execution error: {execution_error}")
                yield f"data: {safe_json_dumps({'type': 'error', 'message': str(execution_error)})}\n\n"
                break

            # Small delay to avoid busy waiting
            await asyncio.sleep(0.1)

        logger.info(
            f"Real-time social streaming completed. execution_completed={execution_completed}, execution_error={execution_error}"
        )

        # Wait for thread to complete
        execution_thread.join(timeout=2)

        # Send any remaining events
        final_events = []
        while not event_queue.empty():
            try:
                final_events.append(event_queue.get_nowait())
            except queue.Empty:
                break

        for event in final_events:
            yield f"data: {safe_json_dumps(event)}\n\n"

        # Handle final state management
        if plan_run_result:
            plan_run_id = str(plan_run_result.id)

            if plan_run_result.state == PlanRunState.NEED_CLARIFICATION:
                # Store plan run for clarification handling
                running_plans[plan_run_id] = {
                    "social_portia": social_portia,
                    "caption_run": plan_run_result,
                    "request": request,
                    "current_phase": "content_validation",
                }

                # Get clarifications and send them
                clarifications = plan_run_result.get_outstanding_clarifications()
                clarification_data = []
                for clarification in clarifications:
                    clarification_info = {
                        "id": str(clarification.id),
                        "category": clarification.category.value,
                        "user_guidance": clarification.user_guidance,
                        "argument_name": getattr(clarification, "argument_name", None),
                        "options": getattr(clarification, "options", None),
                        "resolved": clarification.resolved,
                    }
                    clarification_data.append(clarification_info)

                # Get generated captions if available
                generated_captions = None
                if (
                    hasattr(plan_run_result.outputs, "final_output")
                    and plan_run_result.outputs.final_output
                ):
                    generated_captions = plan_run_result.outputs.final_output.value

                yield f"data: {safe_json_dumps({'type': 'clarification_required', 'plan_run_id': plan_run_id, 'clarifications': clarification_data, 'generated_captions': generated_captions.model_dump() if generated_captions and hasattr(generated_captions, 'model_dump') else generated_captions, 'message': 'User input required to continue'})}\n\n"

            elif plan_run_result.state == PlanRunState.COMPLETE:
                # Store completed plan run
                final_output = (
                    plan_run_result.outputs.final_output.value
                    if hasattr(plan_run_result.outputs, "final_output")
                    and plan_run_result.outputs.final_output
                    else None
                )

                running_plans[plan_run_id] = {
                    "social_portia": social_portia,
                    "generated_captions": final_output,
                    "caption_run": plan_run_result,
                    "request": request,
                    "current_phase": "completed",
                }

                # Stream is complete, exit the function
                logger.info(
                    f"Social scheduler streaming completed successfully for plan {plan_run_id}"
                )
                return

    except Exception as e:
        logger.error(f"Error in social scheduler streaming: {str(e)}")
        logger.error(traceback.format_exc())
        yield f"data: {safe_json_dumps({'type': 'error', 'message': str(e)})}\n\n"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
