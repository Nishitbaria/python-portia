from portia import (
    Step,
    Tool,
    ToolHardError,
    Clarification,
    ClarificationCategory,
    PlanRun,
    PlanBuilderV2,
    Input,
    ActionClarification,
    InputClarification,
    MultipleChoiceClarification,
    PlanRunState,
)
from typing import Any, Optional, List
import re
import time
import json
from utils.schema import PostingResult, OutputSpecialId, PredictionPollResult


# -----------------------------
# Manual clarification handling
# -----------------------------
def handle_outstanding_clarifications(run, portia_instance):
    """
    Loop while there are outstanding clarifications and take user input.
    Any non-'yes' answer is passed as the edit instruction, which the hook will apply.
    """
    safety = 0
    while True:
        safety += 1
        if safety > 10:
            print("Too many clarification loops; bailing out.")
            return run

        # Fetch pending clarifications (SDKs vary; try both)
        clars = getattr(run, "get_outstanding_clarifications", None)
        clars = clars() if callable(clars) else getattr(run, "clarifications", []) or []
        pending = [c for c in clars if not getattr(c, "resolved", False)]
        if not pending:
            return run

        for clar in pending:
            print("\n--- Clarification ---")
            print(getattr(clar, "user_guidance", ""))

            # Handle OAuth authentication clarifications
            if isinstance(clar, ActionClarification):
                print("---------------------")
                print(
                    "OAuth authentication required. Please click the link below to authenticate:"
                )
                print(clar.action_url)
                print("After authentication, press Enter to continue...")
                input()

                # Wait for the authentication to complete
                try:
                    run = portia_instance.wait_for_ready(run)
                except Exception as e:
                    print(f"Error waiting for authentication: {e}")
                    print(
                        "Please ensure you've completed the authentication and try again."
                    )
                    input("Press Enter to retry...")
                    run = portia_instance.wait_for_ready(run)
                continue

            # Handle other types of clarifications
            print("---------------------")
            if isinstance(clar, MultipleChoiceClarification):
                print("Options:")
                for i, option in enumerate(getattr(clar, "options", []), 1):
                    print(f"{i}. {option}")
                user_resp = input("Enter your choice (number): ").strip()
                try:
                    choice_idx = int(user_resp) - 1
                    user_resp = clar.options[choice_idx]
                except (ValueError, IndexError):
                    print("Invalid choice, using as-is")
            else:
                user_resp = input("Your answer: ").strip()

            # Prefer the new-style API
            answered = False
            answer_fn = getattr(portia_instance, "answer_clarification", None)
            if callable(answer_fn):
                try:
                    answer_fn(
                        plan_id=run.plan.id,
                        plan_run_id=run.id,
                        clarification_id=getattr(clar, "id", None),
                        answer=user_resp,
                    )
                    answered = True
                except Exception:
                    answered = False

            # Fallback to older API
            if not answered:
                resolve_fn = getattr(portia_instance, "resolve_clarification", None)
                if callable(resolve_fn):
                    resolve_fn(clar, user_resp, run)

        # Resume the plan (SDKs vary; try both)
        run = _resume_plan_run(run, portia_instance)


def _resume_plan_run(run, portia_instance):
    cont = getattr(portia_instance, "continue_plan", None)
    if callable(cont):
        try:
            return cont(plan_id=run.plan.id, plan_run_id=run.id)
        except Exception:
            pass
    resume_fn = getattr(portia_instance, "resume", None)
    if callable(resume_fn):
        try:
            return resume_fn(run)
        except Exception:
            pass
    return run


def _resume_plan_run(run, portia_instance) -> Any:
    cont = getattr(portia_instance, "continue_plan", None)
    if callable(cont):
        try:
            return cont(plan_id=run.plan.id, plan_run_id=run.id)
        except Exception:
            pass
    resume_fn = getattr(portia_instance, "resume", None)
    if callable(resume_fn):
        try:
            return resume_fn(run)
        except Exception:
            pass
    return run


def safe_final_value(run) -> Optional[Any]:
    return getattr(
        getattr(getattr(run, "outputs", None), "final_output", None), "value", None
    )


# -------------------------
# Edit-plan (LLM transformer)
# -------------------------
def build_edit_transform_plan():
    """
    A tiny LLM plan that ONLY updates the field(s) implied by `channels`,
    and leaves all other fields exactly as-is.
    Output schema: PostingResult (channels, caption, tweet_text)
    """
    return (
        PlanBuilderV2(
            "Transform social text per user instruction with strict field bounds"
        )
        .input(name="channels", description="instagram | twitter | both")
        .input(name="caption", description="Current Instagram caption (can be null)")
        .input(name="tweet_text", description="Current Twitter text (can be null)")
        .input(name="instruction", description="User-provided change request")
        .llm_step(
            step_name="apply_edits",
            task="""
You will receive:
- channels: "instagram" | "twitter" | "both"
- caption: current caption (nullable)
- tweet_text: current tweet text (nullable)
- instruction: user's requested changes

Rules:
1) If channels == "instagram": 
   - Update ONLY `caption` according to the instruction.
   - Leave `tweet_text` unchanged (return the original value).
2) If channels == "twitter":
   - Update ONLY `tweet_text` according to the instruction.
   - Leave `caption` unchanged (return the original value).
3) If channels == "both":
   - Decide which field(s) the user intended from the instruction:
       * If the instruction mentions "tweet", "twitter", or "X", update ONLY tweet_text.
       * If it mentions "caption", "insta", or "instagram", update ONLY caption.
       * If it's ambiguous or generic (e.g., "make it cuter"), update BOTH fields consistently.
   - Do NOT change 'channels'.
4) Do not add hashtags if the user said not to. Preserve tone requests (e.g., "good morning").
5) Strictly preserve any field you are not tasked to change.
6) Return a PostingResult with the final channels, caption, and tweet_text.
            """,
            inputs=[
                Input("channels"),
                Input("caption"),
                Input("tweet_text"),
                Input("instruction"),
            ],
            output_schema=PostingResult,
        )
        .final_output(output_schema=PostingResult)
        .build()
    )


# -----------------------------
# Image generation utilities
# -----------------------------
def extract_id_and_status(value):
    """Extract prediction ID and status from Replicate response."""

    pred_id = None
    status = None

    # Handle Portia's structured response format
    if hasattr(value, "content") and value.content:
        try:
            # Extract text from the first content item
            text_content = value.content[0].text
            # Parse the JSON array: ["id", "status"]
            parsed_array = json.loads(text_content)
            if isinstance(parsed_array, list) and len(parsed_array) >= 2:
                return parsed_array[0], parsed_array[1]
        except (json.JSONDecodeError, IndexError, AttributeError):
            pass

    # If structured object with id/status attributes
    try:
        pred_id = getattr(value, "id", None)
        status = getattr(value, "status", None)
        if pred_id and status:
            return pred_id, status
    except Exception:
        pass

    # If dict-like
    if isinstance(value, dict):
        pred_id = value.get("id")
        status = value.get("status")
        if pred_id and status:
            return pred_id, status

    # If string representation contains JSON array
    text_val = str(value)
    try:
        # Look for JSON array pattern in the string
        array_match = re.search(r'\["([^"]+)",\s*"([^"]+)"\]', text_val)
        if array_match:
            return array_match.group(1), array_match.group(2)
    except Exception:
        pass

    # If string like: id='...' status='...'
    m_id = re.search(r"id='([^']+)'", text_val)
    m_status = re.search(r"status='([^']+)'", text_val)
    if m_id:
        pred_id = m_id.group(1)
    if m_status:
        status = m_status.group(1)
    return pred_id, status


def poll_prediction_until_complete(portia_instance, prediction_id: str) -> List[str]:
    """Poll Replicate prediction until completion and return image URLs."""
    final_urls: List[str] = []
    terminal_statuses = {"succeeded", "failed", "canceled", "cancelled"}

    while True:
        plan_check = portia_instance.plan(
            f"""
            Call tool 'portia:mcp:custom:mcp.replicate.com:get_predictions' with:
              - id = "{prediction_id}"
            Extract only fields status and output and return exactly:
              {{"status": .status, "output": .output}}
            """
        )
        pr_check = portia_instance.run_plan(
            plan_check, structured_output_schema=PredictionPollResult
        )

        result = pr_check.outputs.final_output.value
        try:
            current_status = result.status
            current_output = result.output
        except Exception:
            # Fallbacks for unexpected shapes
            val = pr_check.outputs.final_output.value
            if isinstance(val, dict):
                current_status = val.get("status")
                current_output = val.get("output")
            else:
                text_val = str(val)
                m_status2 = re.search(
                    r"\bstatus\"?[:=]\s*['\"]?([a-zA-Z]+)['\"]?", text_val
                )
                current_status = m_status2.group(1) if m_status2 else None
                current_output = None

        print(f"Poll: status={current_status}")

        if not current_status or current_status.lower() not in terminal_statuses:
            time.sleep(3)
            continue

        if current_status.lower() != "succeeded":
            raise RuntimeError(
                f"Prediction {prediction_id} ended with status {current_status}"
            )

        # Succeeded
        final_urls = current_output or []
        break

    return final_urls


def build_image_generation_plan():
    """Build a plan for image generation using Replicate Flux-Schnell."""
    return (
        PlanBuilderV2("Generate images using Replicate Flux-Schnell model")
        .input(name="user_prompt", description="The user's image generation prompt")
        .single_tool_agent_step(
            tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
            task="""
            Generate images using Replicate's Flux-Schnell model.
            
            Use these exact parameters:
            - version = "black-forest-labs/flux-schnell"
            - prompt = the user's prompt from input
            - input.num_outputs = 4 (generate 4 images for selection)
            - input.aspect_ratio = "1:1" (Instagram-friendly)
            - input.output_format = "png" (Instagram-safe)
            - input.output_quality = 80
            - input.num_inference_steps = 4
            - input.go_fast = true
            - input.disable_safety_checker = false
            - Prefer = "wait=1"
            - webhook = "https://unbiased-carefully-marmot.ngrok-free.app"
            
            Extract and return only the id and status fields.
            """,
            inputs=[Input("user_prompt")],
            step_name="create_prediction",
        )
        .final_output(output_schema=OutputSpecialId)
        .build()
    )
