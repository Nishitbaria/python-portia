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
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ACCOUNT_ID = os.getenv("MAKE_DOT_COM_ACCOUNT_ID")

openai_config = Config.from_default(
    llm_provider=LLMProvider.OPENAI,
    default_model="openai/gpt-4o",
    openai_api_key=OPENAI_API_KEY,
    storage_class=StorageClass.CLOUD,
    log_level=LogLevel.DEBUG,
)


portia = Portia(
    config=openai_config,
    execution_hooks=create_streaming_hooks("plan_stream.json"),
    tools=(
        PortiaToolRegistry(config=openai_config).with_tool_description(
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
