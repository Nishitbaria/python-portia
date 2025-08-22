import os, json
from typing import Any
from dotenv import load_dotenv
from portia.clarification import UserVerificationClarification
from utils.schema import PostingResult
from portia import (
    Config,
    LLMProvider,
    Portia,
    PortiaToolRegistry,
    StorageClass,
    LogLevel,
    ClarificationCategory,
)
from portia.execution_hooks import ExecutionHooks
from utils.utils_function import (
    SOCIAL_POST_TOOL_ID,
    build_edit_transform_plan,
)
from portia.cli import CLIExecutionHooks


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ACCOUNT_ID = os.getenv("MAKE_DOT_COM_ACCOUNT_ID")


openai_config = Config.from_default(
    llm_provider=LLMProvider.OPENAI,
    default_model="openai/gpt-4o",
    openai_api_key=OPENAI_API_KEY,
    storage_class=StorageClass.CLOUD,
    log_level=LogLevel.INFO,
)


# ---------------------------------------
# Execution hook: before calling the tool
# ---------------------------------------
def clarify_and_apply_edits_before_post(
    tool, args: dict[str, Any], plan_run, step, portia_instance
):
    """
    - Preview the payload before posting.
    - If user says 'yes' -> proceed.
    - Otherwise treat the response as edit instructions and run an LLM edit transform that updates ONLY the relevant fields.
    - Mutate tool args in-place and then proceed.
    """
    if tool.id != SOCIAL_POST_TOOL_ID:
        return None  # only intercept this tool

    # Check if we already raised a USER_VERIFICATION clarification for this step
    prev = plan_run.get_clarification_for_step(ClarificationCategory.USER_VERIFICATION)

    # If first time or unresolved => raise clarification and pause
    if not prev or not prev.resolved:
        guidance = (
            "Generated content:\n\n"
            f"- channels: {args.get('channels')}\n"
            f"- Instagram caption: {args.get('caption')}\n"
            f"- Twitter text: {args.get('tweet_text')}\n"
            f"- image_url: {args.get('image_url')}\n\n"
            "Type 'yes' to approve as-is.\n"
            "Or type your changes (e.g., 'make caption say Good morning, no hashtags'). "
            "If posting to both, mention which one(s) to change."
        )
        return UserVerificationClarification(
            plan_run_id=plan_run.id,
            user_guidance=guidance,
        )

    # If resolved: apply decision. Any non-yes is treated as edit instruction.
    resp = str(prev.response or "").strip()
    if resp.lower() in {"y", "yes", "ok", "approve", "approved", "✅", "👍"}:
        return None  # proceed unchanged

    # Treat as edit instructions
    instruction = resp
    channels = args.get("channels")
    caption = args.get("caption")
    tweet_text = args.get("tweet_text")

    # Run the tiny transform plan to update only the intended field(s)
    edit_plan = build_edit_transform_plan()
    edit_run = portia_instance.run_plan(
        edit_plan,
        plan_run_inputs={
            "channels": channels,
            "caption": caption,
            "tweet_text": tweet_text,
            "instruction": instruction,
        },
        structured_output_schema=PostingResult,
    )
    edited = edit_run.outputs.final_output.value

    # Mutate tool args in-place; preserve unchanged fields exactly as returned
    # Channels must remain the same (the LLM is instructed not to change it).
    args["channels"] = edited.channels or channels

    # Respect channels: only the relevant field(s) should have changed.
    # We trust the LLM output (it returns old values for fields it didn't touch).
    args["caption"] = edited.caption
    args["tweet_text"] = edited.tweet_text

    # Never touch image_url here.
    return None


# Wrapper function that execution hooks can call (only 4 parameters)
def clarify_and_apply_edits_wrapper(tool, args: dict[str, Any], plan_run, step):
    return clarify_and_apply_edits_before_post(tool, args, plan_run, step, portia)


# --------------------------------------
# Execution hook: after calling the tool
# --------------------------------------
# Storage for the last payload that actually went out
_POSTED_PAYLOAD: dict | None = None
SOCIAL_POST_TOOL_ID = (
    "portia:mcp:custom:us2.make.com:s2795860_mcp_social_post_ig_x_both"
)


def capture_post_payload_after_post(*hook_args, **hook_kwargs):
    """
    Compatible with both:
      (tool, args, result, step)
    and (tool, args, result, plan_run, step)
    """
    # Positional extraction
    if not hook_args:
        return None
    tool = hook_args[0]

    # Try keyword args first (if SDK ever adds them)
    args_dict = hook_kwargs.get("args")
    result = hook_kwargs.get("result")

    # Fallback to positional mapping
    if args_dict is None:
        # Expected shapes:
        # [tool, args, result, step] -> len == 4
        # [tool, args, result, plan_run, step] -> len == 5
        if len(hook_args) >= 3:
            args_dict = hook_args[1]
        if len(hook_args) >= 3 and result is None:
            result = hook_args[2]

    # Safety check and capture
    if getattr(tool, "id", None) == SOCIAL_POST_TOOL_ID and isinstance(args_dict, dict):
        global _POSTED_PAYLOAD
        _POSTED_PAYLOAD = {
            "channels": args_dict.get("channels"),
            "caption": args_dict.get("caption"),
            "tweet_text": args_dict.get("tweet_text"),
            "image_url": args_dict.get("image_url"),
        }
    return None


portia = Portia(
    config=openai_config,
    execution_hooks=ExecutionHooks(
        before_tool_call=clarify_and_apply_edits_wrapper,
        after_tool_call=capture_post_payload_after_post,
    ),
    tools=(
        PortiaToolRegistry(config=openai_config).with_tool_description(
            "portia:mcp:custom:us2.make.com:s2795860_mcp_social_post_ig_x_both",
            f"""
    Use this tool to post social content to Twitter, Instagram, or both via Make.com.

    Input payload fields:
    - channels: "twitter" | "instagram" | "both"
      → decides where to post.
    - caption: Text caption (required, used for Instagram and as fallback for Twitter).
    - tweet_text: Optional tweet text (if empty, caption will be used).
    - image_url: Required for Instagram posts (publicly accessible image/video URL).

    Behavior:
    - If channels = "instagram": creates a new Instagram post with image_url + caption.
    - If channels = "twitter": posts a tweet with tweet_text (or caption if missing).
    - If channels = "both": posts to Instagram first, then to Twitter in sequence.

    Example payload:
    {{
      "channels": "both",
      "caption": "New feature live! 🚀",
      "tweet_text": "It's live. Details inside.",
      "image_url": "https://cdn.example.com/hero.jpg",
    }}
    """,
        )
    ),
)
