# Basic call to replicate
# Speific Instruction
# Clarification
# Execution Context
import json
import os
from dotenv import load_dotenv
from portia import (
    Config,
    DefaultToolRegistry,
    LLMProvider,
    Portia,
    PortiaToolRegistry,
    StorageClass,
    LogLevel,
    execution_hooks,
    PlanRunState,
    MultipleChoiceClarification,
)
from portia.cli import CLIExecutionHooks

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ACCOUNT_ID = os.getenv("MAKE_DOT_COM_ACCOUNT_ID")
end_user = "Vinayak_Vispute-2"

openai_config = Config.from_default(
    llm_provider=LLMProvider.OPENAI,
    default_model="openai/gpt-4o",
    openai_api_key=OPENAI_API_KEY,
    storage_class=StorageClass.CLOUD,
    log_level=LogLevel.ERROR,
)

portia = Portia(
    config=openai_config,
    execution_hooks=CLIExecutionHooks(),
    tools=(
        PortiaToolRegistry(config=openai_config)
        .with_tool_description(
            "portia:mcp:custom:mcp.replicate.com:create_predictions",
            """
    Use this tool to generate images with Replicate's Flux-Schnell model.
    Always include:
      - version = "black-forest-labs/flux-schnell"
      - prompt = user's description
    Optional fields (decide from user request):
      - input.num_outputs (default 1, range 1-4)
      - input.aspect_ratio (default "1:1")
      - input.output_format (default "webp")
      - input.output_quality (default 80)
      - input.num_inference_steps (default 4)
      - input.go_fast (default true)
      - input.disable_safety_checker (default false)
    Always set Prefer = "wait".
    
    If input.num_outputs > 1:
      - return all image URLs (using jq_filter = .output).
      - ask the user for clarification with a multiple-choice prompt:
        "Multiple images were generated. Please choose one of the following URLs."
      - pause execution and let the user select one.
      - continue the plan using only the chosen URL.
    """,
        )
        .with_tool_description(
            "portia:mcp:custom:us2.make.com:s2795860_integration_instagram_for_business_facebook_log",
            f"""
     Use this tool to post to instagram with accountId {ACCOUNT_ID}.
    """,
        )
    ),
)


user_prompt = input("Enter the image prompt: ")

plan = portia.plan(user_prompt)

print("==Plans:===============\n")
print(plan.pretty_print())
print("==Plans End===============\n")

plan_run = portia.run_plan(
    plan,
    end_user=end_user,
)

# Handle clarifications if needed
while plan_run.state == PlanRunState.NEED_CLARIFICATION:
    # If clarifications are needed, resolve them before resuming the plan run
    for clarification in plan_run.get_outstanding_clarifications():
        # For each clarification, prompt the user for input
        print(f"{clarification.user_guidance}")
        user_input = input(
            "Please enter a value:\n"
            + (
                ("\n".join(clarification.options) + "\n")
                if isinstance(clarification, MultipleChoiceClarification)
                else ""
            )
        )
        # Resolve the clarification with the user input
        plan_run = portia.resolve_clarification(clarification, user_input, plan_run)

    # Once clarifications are resolved, resume the plan run
    plan_run = portia.resume(plan_run)


raw_output = plan_run.outputs.final_output.value  # type: ignore
print(type(raw_output))

clean_url = None

try:
    # Case 1: raw_output is a JSON string
    if isinstance(raw_output, str):
        print("raw_output is a string")
        parsed = json.loads(raw_output)
        if isinstance(parsed, dict) and "content" in parsed:
            text_val = parsed["content"][0]["text"]
            clean_url = text_val.strip('"')
        else:
            # maybe it's already the URL string
            clean_url = raw_output.strip('"')
    # Case 2: raw_output already a dict
    elif isinstance(raw_output, dict):
        print("raw_output is a dict")
        text_val = raw_output["content"][0]["text"]
        clean_url = text_val.strip('"')
except Exception as e:
    print("raw_output is a string")
    clean_url = str(raw_output).strip('"')
    print(f"[WARN] Could not parse final_output: {e}")

print(f"Click here => {clean_url}")
