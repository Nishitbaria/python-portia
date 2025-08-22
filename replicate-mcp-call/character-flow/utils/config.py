import os
from dotenv import load_dotenv
from portia import (
    Config,
    LLMProvider,
    Portia,
    PortiaToolRegistry,
    StorageClass,
    LogLevel,
)
from portia.execution_hooks import ExecutionHooks

# from utils.hooks import pass


load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ACCOUNT_ID = os.getenv("MAKE_DOT_COM_ACCOUNT_ID")


anthropic_config = Config.from_default(
    llm_provider=LLMProvider.ANTHROPIC,
    default_model="claude-sonnet-4",
    anthropic_api_key=ANTHROPIC_API_KEY,
    storage_class=StorageClass.CLOUD,
    log_level=LogLevel.DEBUG,
)


portia = Portia(
    config=anthropic_config,
    execution_hooks=ExecutionHooks(),
    tools=(
        PortiaToolRegistry(config=anthropic_config)
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
            Always set Prefer = "wait=1".
            Also set webhook = "https://unbiased-carefully-marmot.ngrok-free.app"
            Extract and return only status and id using jq_filter
            Return the id and status only, in the format of a id string and status string, nothing else
            MAKE ONLY ONE CALL
            """,
        )
        .with_tool_description(
            "portia:mcp:custom:mcp.replicate.com:get_predictions",
            """
            Use this tool to fetch a Replicate prediction by its id.
            Always include:
              - id = the prediction id string you are checking
            Prefer extracting only the fields status and output using jq_filter = {status: .status, output: .output}.
            Return exactly a JSON object with:
              - status: string (e.g. "starting", "processing", "succeeded", "failed")
              - output: list of image URL strings if present, otherwise null
            MAKE ONLY ONE CALL.
            """,
        )
    ),
)
