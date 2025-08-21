task0 = """
Find the pricing for Chatgpt from OpenAI, Claude from Antropic and Grok AI:
1) OpenAI ChatGPT (chatgpt.com)
2) Anthropic Claude (claude.ai)
3) xAI Grok (grok.com / help.x.com)

Give a summary of the pricing information for each in tabular format.
"""

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
    McpToolRegistry,
    execution_hooks,
)
from portia.cli import CLIExecutionHooks
from pydantic import BaseModel, Field
from typing import Dict, List


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
end_user = "Vinayak_Vispute-1"


class UrlList(BaseModel):
    urls: Dict[str, List[str]] = Field(
        description="A dictionary mapping chatbot names to their respective URLs for pricing and help pages.",
    )


openai_config = Config.from_default(
    llm_provider=LLMProvider.OPENAI,
    default_model="openai/gpt-4o",
    openai_api_key=OPENAI_API_KEY,
    storage_class=StorageClass.CLOUD,
)

if not PERPLEXITY_API_KEY:
    raise ValueError("PERPLEXITY_API_KEY is not set in the environment variables.")


perplexity_tool_registry = McpToolRegistry.from_stdio_connection(
    server_name="perplexity-ask",
    command="npx",
    args=["-y", "server-perplexity-ask"],
    env={"PERPLEXITY_API_KEY": PERPLEXITY_API_KEY},
)

portia = Portia(
    config=openai_config,
    execution_hooks=CLIExecutionHooks(),
    tools=perplexity_tool_registry
    + PortiaToolRegistry(config=openai_config)
    + DefaultToolRegistry(config=openai_config),
)

plan = portia.plan(task0)

print("==Plans:===============\n")
print(plan.pretty_print())
print("==Plans End===============\n")
plan_run = portia.run_plan(
    plan,
    end_user=end_user,
)

print(plan_run.model_dump_json(indent=2))
