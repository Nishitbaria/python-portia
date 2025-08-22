"""
Execution hooks for social media posting workflow.
"""

from typing import Any
from portia.clarification import UserVerificationClarification
from portia import ClarificationCategory
from utils.schema import PostingResult
from utils.utils_function import build_edit_transform_plan

# Constants
SOCIAL_POST_TOOL_ID = (
    "portia:mcp:custom:us2.make.com:s2795860_mcp_social_post_ig_x_both"
)

# Storage for the last payload that actually went out
_POSTED_PAYLOAD: dict | None = None


def before_social_post_hook(tool, args: dict[str, Any], plan_run, step):
    """
    Hook that runs before the social posting tool is called.

    - Shows preview of content and asks for user approval
    - If user provides edits, applies them via LLM transform
    - Mutates args in-place with edited content
    """
    if tool.id != SOCIAL_POST_TOOL_ID:
        return None  # only intercept our social posting tool

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

    # Apply edit instructions
    _apply_content_edits(args, resp)
    return None


def after_social_post_hook(*hook_args, **hook_kwargs):
    """
    Hook that runs after the social posting tool is called.
    Captures the payload that was actually sent.
    """
    # Handle different hook signature variations
    if not hook_args:
        return None
    tool = hook_args[0]

    # Extract args from either keyword or positional arguments
    args_dict = hook_kwargs.get("args")
    if args_dict is None and len(hook_args) >= 2:
        args_dict = hook_args[1]

    # Capture payload if this was our social posting tool
    if getattr(tool, "id", None) == SOCIAL_POST_TOOL_ID and isinstance(args_dict, dict):
        global _POSTED_PAYLOAD
        _POSTED_PAYLOAD = {
            "channels": args_dict.get("channels"),
            "caption": args_dict.get("caption"),
            "tweet_text": args_dict.get("tweet_text"),
            "image_url": args_dict.get("image_url"),
        }
    return None


def _apply_content_edits(args: dict[str, Any], instruction: str):
    """
    Apply user's edit instruction to the content using LLM transform.
    Mutates args in-place.
    """
    # Import here to avoid circular dependency
    from utils.config import portia

    channels = args.get("channels")
    caption = args.get("caption")
    tweet_text = args.get("tweet_text")

    # Run the edit transform plan
    edit_plan = build_edit_transform_plan()
    edit_run = portia.run_plan(
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

    # Update args in-place with edited content
    args["channels"] = edited.channels or channels
    args["caption"] = edited.caption
    args["tweet_text"] = edited.tweet_text


def get_last_posted_payload() -> dict | None:
    """Get the last payload that was actually posted."""
    return _POSTED_PAYLOAD
