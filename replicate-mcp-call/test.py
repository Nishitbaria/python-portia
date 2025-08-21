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
from portia.cli import CLIExecutionHooks
import re
from pydantic import BaseModel

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
    execution_hooks=CLIExecutionHooks(),
    tools=(
        PortiaToolRegistry(config=openai_config)
        .with_tool_description(
            "portia:mcp:custom:mcp.replicate.com:create_models_predictions",
            """
            Use this tool to generate video with Replicate's kling-v1.6-standard model.
            Always include:
              - model = "kwaivgi/kling-v1.6-standard"
              - prompt = user's description
            Always set Prefer = "wait=5".
            Also set webhook = "https://unbiased-carefully-marmot.ngrok-free.app"
            Extract and return only status and  id using jq_filter
            Return the id and status only, in the format of a id string and status string, nothing else
            MAKE ONLY ONE CALL
            """,
        )
        .with_tool_description(
            "portia:mcp:custom:us2.make.com:s2795860_integration_instagram_for_business_facebook_log",
            f"""
            Use this tool to post an video to Instagram with accountId {ACCOUNT_ID}.
            """,
        )
    ),
)


class OutputSpecialId(BaseModel):
    id: str
    status: str


# -------- Plan 1: Generate video --------
user_prompt = input("Enter your Video prompt: ")

plan1 = portia.plan(f"Generate a video of {user_prompt} using kling-v1.6-standard")
print("\n== Plan 1 ==")
print(plan1.pretty_print())

pr1 = portia.run_plan(plan1, structured_output_schema=OutputSpecialId, end_user="qwqwq")

print("pr1.outputs.final_output.value", pr1.outputs.final_output.value)
