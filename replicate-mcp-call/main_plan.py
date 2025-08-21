from portia.builder.plan_builder_v2 import PlanBuilderV2
from dotenv import load_dotenv
import os
import json
from portia import (
    Config,
    DefaultToolRegistry,
    LLMProvider,
    Portia,
    PortiaToolRegistry,
    StorageClass,
    LogLevel,
    execution_hooks,
)
from portia.builder.reference import Input, StepOutput
from portia.cli import CLIExecutionHooks
from tools.image_picker_tool import ImagePickerTool

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

registry = PortiaToolRegistry(config=openai_config)
registry = registry.with_tool_description(
    "portia:mcp:custom:mcp.replicate.com:create_predictions",
    """
Use this tool to generate images with Replicate's Flux-Schnell model.
Always include:
  - version = "black-forest-labs/flux-schnell"
  - prompt = user's description
Optional fields (decide from user request):
  - input.num_outputs (default 1, range 1-4)
  - input.aspect_ratio (default "1:1")
  - input.output_format (default 80)
  - input.num_inference_steps (default 4)
  - input.go_fast (default true)
  - input.disable_safety_checker (default false)
Always set Prefer = "wait".

If input.num_outputs > 1:
  - return all image URLs (using jq_filter = .output).
  - do NOT finalize the output.
  - instead, create a clarification step with multiple-choice options, one for each URL.
  - wait for the user’s choice (CLIExecutionHooks will handle the prompt).
  - once the user chooses, continue with the selected URL.
    """,
).with_tool_description(
    "portia:mcp:custom:us2.make.com:s2795860_integration_instagram_for_business_facebook_log",
    f"""
 Use this tool to post to instagram with accountId {ACCOUNT_ID}.
""",
)

# Register local tool for picking images
registry.with_tool(ImagePickerTool())

portia = Portia(
    config=openai_config,
    execution_hooks=CLIExecutionHooks(),
    tools=registry,
)

user_prompt = input("Enter the image prompt: ")


def build_replicate_input(prompt: str) -> dict:
    return {
        "prompt": prompt,
        "num_outputs": 4,
        "aspect_ratio": "1:1",
        # IMPORTANT: make the media Instagram-compatible (use png or jpg)
        "output_format": "png",  # avoid webp to prevent IG 9004 error
        "output_quality": 80,
        "num_inference_steps": 4,
        "go_fast": True,
        "disable_safety_checker": False,
    }


plan = (
    PlanBuilderV2("Generate 4 images, ask user to pick, then post to Instagram")
    .input(name="prompt", description="Prompt for Replicate")
    .function_step(
        function=build_replicate_input,
        args={"prompt": Input("prompt")},
        step_name="build_replicate_args",
    )
    .invoke_tool_step(
        tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
        args={
            "input": StepOutput("build_replicate_args"),
            "version": "black-forest-labs/flux-schnell",
            "Prefer": "wait",
            "jq_filter": ".output",  # returns a list of URLs
        },
        step_name="generate_images",
    )
    .invoke_tool_step(
        tool="image_picker_tool",
        args={"urls": StepOutput("generate_images")},
        step_name="pick_image",
    )
    .invoke_tool_step(
        tool="portia:mcp:custom:us2.make.com:s2795860_integration_instagram_for_business_facebook_log",
        args={
            "image_url": StepOutput("pick_image"),
            "caption": "Posted via Portia 🤖",
            "accountId": ACCOUNT_ID,
        },
        step_name="post_instagram",
    )
    .final_output()
    .build()
)

plan_run = portia.run_plan(
    plan,
    end_user=end_user,
    plan_run_inputs={"prompt": user_prompt},
)


raw_output = plan_run.outputs.final_output.value  # type: ignore
print(type(raw_output))
