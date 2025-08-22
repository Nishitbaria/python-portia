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
from utils.hooks import (
    before_social_post_hook,
    after_social_post_hook,
    SOCIAL_POST_TOOL_ID,
)


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


portia = Portia(
    config=openai_config,
    execution_hooks=ExecutionHooks(
        before_tool_call=before_social_post_hook,
        after_tool_call=after_social_post_hook,
    ),
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
        .with_tool_description(
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
