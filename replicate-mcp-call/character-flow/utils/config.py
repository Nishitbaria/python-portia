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
from .streaming_hooks import create_streaming_hooks

# from utils.hooks import pass


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ACCOUNT_ID = os.getenv("MAKE_DOT_COM_ACCOUNT_ID")

openai_config = Config.from_default(
    llm_provider=LLMProvider.OPENAI,
    default_model="openai/gpt-4o",
    anthropic_api_key=OPENAI_API_KEY,
    storage_class=StorageClass.CLOUD,
    log_level=LogLevel.DEBUG,
)


portia = Portia(
    config=openai_config,
    execution_hooks=create_streaming_hooks("plan_stream.json"),
    tools=(
        PortiaToolRegistry(config=openai_config)
        .with_tool_description(
            "portia:mcp:custom:mcp.replicate.com:create_predictions",
            """
            Use this tool to create predictions with Replicate models.
            
            For image generation with Flux-Schnell:
            - version = "black-forest-labs/flux-schnell"
            - prompt = user's description
            - Optional fields: input.num_outputs (1-4), input.aspect_ratio ("1:1"), input.output_format ("webp"), input.output_quality (80), input.num_inference_steps (4), input.go_fast (true), input.disable_safety_checker (false)
            - Prefer = "wait=1"
            - webhook = "https://unbiased-carefully-marmot.ngrok-free.app"
            - jq_filter to extract status and id
            
            For product description with Claude-4-Sonnet:
            - version = "anthropic/claude-4-sonnet"
            - input.prompt = "Write Prompt for this product"
            - input.system_prompt = [The detailed system prompt for product description]
            - input.image = [product image URL]
            - jq_filter = ".output"
            - Prefer = "wait"
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
