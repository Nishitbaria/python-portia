from portia import (
    Step,
    Tool,
    ToolHardError,
    Clarification,
    ClarificationCategory,
    PlanRun,
)
from portia.clarification import UserVerificationClarification
from typing import Any, Optional


# def clarify_before_posting(
#     tool: Tool,
#     args: dict[str, Any],
#     plan_run: PlanRun,
#     step: Step,
# ) -> Clarification | None:
#     # Only trigger on your posting tool
#     if tool.id != "portia:mcp:custom:us2.make.com:s2795860_mcp_social_post_ig_x_both":
#         return None

#     # Check if already clarified
#     previous = plan_run.get_clarification_for_step(
#         ClarificationCategory.USER_VERIFICATION
#     )
#     if not previous or not previous.resolved:
#         # First time asking for approval
#         return UserVerificationClarification(
#             plan_run_id=plan_run.id,
#             user_guidance=(
#                 f"Generated content:\n\n"
#                 f"Instagram caption: {args.get('caption')}\n"
#                 f"Twitter text: {args.get('tweet_text')}\n\n"
#                 f"Do you approve this? (yes/no). "
#                 f"If 'no', please provide the changes you'd like."
#             ),
#         )

#     # If user said "no", stop or modify
#     if str(previous.response).lower() not in ["y", "yes"]:
#         raise ToolHardError(
#             "User rejected the generated captions. Please update them and retry."
#         )

#     return None


SOCIAL_POST_TOOL_ID = (
    "portia:mcp:custom:us2.make.com:s2795860_mcp_social_post_ig_x_both"
)


# -----------------------------
# Execution Hook: before_tool_call
# -----------------------------
# Raise a USER_VERIFICATION clarification right before calling the Make.com tool.
def clarify_before_social_post(tool, args: dict[str, Any], plan_run, step):
    """
    If the upcoming tool call is the Make.com social-post tool, raise a
    USER_VERIFICATION clarification with a tidy preview of what's about to be posted.
    The run will pause until you manually answer in the console.
    """
    if tool.id != SOCIAL_POST_TOOL_ID:
        return None  # Only intercept our social-post tool

    # If there is already a USER_VERIFICATION clarification for this step and it's resolved,
    # decide based on the user's prior answer.
    previous = plan_run.get_clarification_for_step(
        ClarificationCategory.USER_VERIFICATION
    )
    if previous and previous.resolved:
        verdict = str(previous.response or "").strip().lower()
        if verdict in {"y", "yes", "ok", "approve", "approved", "✅", "👍"}:
            return None  # proceed with tool call
        # If the user rejected, hard-stop the tool to avoid accidental posting
        raise ToolHardError(
            f"User rejected tool call to {tool.name} with args {args!r}"
        )

    # Otherwise, raise a new clarification (run will pause here).
    ig_caption = args.get("caption")
    tweet_text = args.get("tweet_text")
    image_url = args.get("image_url")

    guidance = (
        "Generated content:\n\n"
        f"Instagram caption: {ig_caption}\n"
        f"Twitter text: {tweet_text}\n"
        f"Image URL: {image_url}\n\n"
        "Do you approve this? (yes/no). If 'no', you can type your revised caption/tweet text instead."
    )

    return UserVerificationClarification(
        plan_run_id=plan_run.id,
        user_guidance=guidance,
    )


# -----------------------------
# Manual clarification handling
# -----------------------------
def handle_outstanding_clarifications(run, portia_instance) -> Any:
    """
    Loop while there are outstanding clarifications.
    For USER_VERIFICATION:
      - 'yes'/'y' approves and we resume.
      - Anything else is treated as a rejection *or* as revised text:
        - If it looks like a short "no", we cancel posting (by answering 'no').
        - Otherwise, we treat the response as replacement text for caption/tweet.
          We store it back as the clarification's answer (the hook can read it on resume).
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
            print("---------------------")
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

        # Loop again in case new clarifications are raised on resume


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
