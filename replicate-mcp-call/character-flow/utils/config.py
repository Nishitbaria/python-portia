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
from portia import InMemoryToolRegistry

# from utils.hooks import pass


load_dotenv()
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") \
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ACCOUNT_ID = os.getenv("MAKE_DOT_COM_ACCOUNT_ID")

openai_config = Config.from_default(
    llm_provider=LLMProvider.OPENAI,
    default_model="openai/gpt-4o",
    openai_api_key=OPENAI_API_KEY,
    storage_class=StorageClass.CLOUD,
    log_level=LogLevel.DEBUG,
)


# Custom tools will be imported and registered separately to avoid circular imports

# Create the base tool registry with MCP tools
mcp_tool_registry = (
    PortiaToolRegistry(config=openai_config)
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
    .with_tool_description(
        "portia:mcp:custom:us2.make.com:s2825571_on_demand_add_row_to_sheet",
        f"""
Use this tool to add a row to a Google Sheet for tracking UGC content generation.

Input payload fields:
- media_url: The generated video URL from the UGC creation process (required)
- instagram_caption: Text caption for Instagram posts (required)
- date_time: Current timestamp in ISO format "2025-08-23T11:30:00.000Z" (IST timezone)
- twitter_post: Tweet text for Twitter posts (required if channel is "both" or "twitter", otherwise can be None/empty)
- channel: Target social media platform - "both" | "instagram" | "twitter"
  → "both": posting to both Instagram and Twitter
  → "instagram": posting only to Instagram
  → "twitter": posting only to Twitter

Field requirements based on channel:
- If channel = "both" or "twitter": twitter_post is required
- If channel = "instagram": twitter_post can be None or empty
- media_url and instagram_caption are always required
- date_time should be current timestamp in IST timezone

Example payload:
{{
  "media_url": "https://replicate.delivery/abc123/video.mp4",
  "instagram_caption": "Check out this amazing product! #beauty #skincare",
  "date_time": "2025-08-23T11:30:00.000Z",
  "twitter_post": "Amazing product launch! Details in bio.",
  "channel": "both"
}}
""",
    )
)

def get_portia_with_custom_tools():
    """Get Portia instance with custom tools registered"""
    # Import here to avoid circular imports
    from social_scheduler import ContentValidationTool, TimeSchedulingTool, ContentRevisionTool
    
    # Create custom tool registry
    custom_tool_registry = InMemoryToolRegistry.from_local_tools([
        ContentValidationTool(),
        TimeSchedulingTool(),
        ContentRevisionTool()
    ])
    
    # Combine registries
    combined_registry = mcp_tool_registry + custom_tool_registry
    
    return Portia(
        config=openai_config,
        execution_hooks=ExecutionHooks(),
        tools=combined_registry
    )

# Create the default Portia instance (without custom tools for now)
portia = Portia(
    config=openai_config,
    execution_hooks=ExecutionHooks(),
    tools=mcp_tool_registry
)
