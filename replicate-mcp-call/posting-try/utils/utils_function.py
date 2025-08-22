from portia import (
    Step,
    Tool,
    ToolHardError,
    Clarification,
    ClarificationCategory,
    PlanRun,
    PlanBuilderV2,
    Input,
)
from typing import Any, Optional
from utils.schema import PostingResult


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
