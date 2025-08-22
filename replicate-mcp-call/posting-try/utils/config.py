import os, json
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
from utils.utils_function import clarify_before_posting, clarify_before_social_post
from portia.cli import CLIExecutionHooks


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
    execution_hooks=ExecutionHooks(before_tool_call=clarify_before_social_post),
    tools=(
        PortiaToolRegistry(config=openai_config).with_tool_description(
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
