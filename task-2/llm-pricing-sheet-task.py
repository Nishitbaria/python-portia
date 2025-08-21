task = """
Step 1 — Perplexity (URL curation only)
You are a strict URL curator. Find the current OFFICIAL pricing/help pages needed to extract CONSUMER “chatbot access” pricing for:
1) OpenAI ChatGPT (chatgpt.com)
2) Anthropic Claude (claude.ai)
3) xAI Grok (grok.com / help.x.com)

Rules:
- Prefer official pricing/help/FAQ pages over blogs or news.
- Return ONLY a compact JSON with keys: {\"chatgpt_urls\":[], \"claude_urls\":[], \"grok_urls\":[]}.
- Each array must contain 1-4 canonical URLs (no duplicates, no tracking params).
- Do NOT include commentary.

STRICT OUTPUT INSTRUCTIONS (MANDATORY):
- Return RAW JSON only. No prose, no code fences, no backticks, no Markdown.
- The response MUST start with '{' and end with '}'.
- Use only double quotes, no trailing commas.
- URLs must be canonical https links without query parameters or fragments.
- If unsure for a provider, return an empty array for that key.

Step 2 — Firecrawl (fetch and clean)
Run Firecrawl on each URL from step 1. Ask Firecrawl to return clean text/Markdown. If your tool allows a prompt, use:

Crawl each provided URL at depth 0.
Return the page content as plain Markdown (no boilerplate navigation).
Include page title, last-modified if available, and full canonical URL at the top.

Step 3 — Perplexity (structured extraction)
Goal: turn Firecrawl text into the pricing JSON.
You are a pricing extraction agent. Use ONLY the Firecrawl page texts below (treat them as ground truth). 
Extract CONSUMER chatbot access pricing for ChatGPT, Claude, and Grok.

Output currency preference keep USD.

INPUT PAGES (verbatim from Firecrawl):

REQUIREMENTS:
1) Extract only clearly stated plans and prices.
2) If a plan says “from $X”, use \"price_from\".
3) If a plan is region-limited or bundled (e.g., access via X Premium+), put that in \"notes\" and \"availability\".
4) Every plan MUST include a \"sources\" array with the exact canonical URLs you used.
5) If something is unclear on all supplied pages, set that numeric field to null and add a concise \"notes\".
"""
import os
from dotenv import load_dotenv
from portia import (
    Config,
    LLMProvider,
    Portia,
    PortiaToolRegistry,
    StorageClass,
    LogLevel,
    McpToolRegistry,
)
from portia.cli import CLIExecutionHooks

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
end_user = "Vinayak_Vispute"

# JSON schema for structured extraction (Step 3)
# PRICING_SCHEMA = """
# {
#   "type": "object",
#   "properties": {
#     "chatgpt": {
#       "type": "array",
#       "items": {
#         "type": "object",
#         "properties": {
#           "plan": {"type": "string"},
#           "price_usd": {"type": ["number", "null"]},
#           "price_from": {"type": ["number", "null"]},
#           "billing_period": {"type": ["string", "null"]},
#           "availability": {"type": ["string", "null"]},
#           "notes": {"type": ["string", "null"]},
#           "sources": {"type": "array", "items": {"type": "string"}}
#         },
#         "required": ["plan", "sources"]
#       }
#     },
#     "claude": {
#       "type": "array",
#       "items": {
#         "type": "object",
#         "properties": {
#           "plan": {"type": "string"},
#           "price_usd": {"type": ["number", "null"]},
#           "price_from": {"type": ["number", "null"]},
#           "billing_period": {"type": ["string", "null"]},
#           "availability": {"type": ["string", "null"]},
#           "notes": {"type": ["string", "null"]},
#           "sources": {"type": "array", "items": {"type": "string"}}
#         },
#         "required": ["plan", "sources"]
#       }
#     },
#     "grok": {
#       "type": "array",
#       "items": {
#         "type": "object",
#         "properties": {
#           "plan": {"type": "string"},
#           "price_usd": {"type": ["number", "null"]},
#           "price_from": {"type": ["number", "null"]},
#           "billing_period": {"type": ["string", "null"]},
#           "availability": {"type": ["string", "null"]},
#           "notes": {"type": ["string", "null"]},
#           "sources": {"type": "array", "items": {"type": "string"}}
#         },
#         "required": ["plan", "sources"]
#       }
#     }
#   },
#   "required": ["chatgpt", "claude", "grok"]
# }
# """


google_config = Config.from_default(
    llm_provider=LLMProvider.OPENAI,
    default_model="openai/gpt-4o",
    openai_api_key=OPENAI_API_KEY,
    storage_class=StorageClass.DISK,
    default_log_level=LogLevel.DEBUG,
)

# Firecrawl mcp url https://mcp.firecrawl.dev/{FIRECRAWL_API_KEY}/sse
firecrawl_mcp_tool_registry = McpToolRegistry.from_sse_connection(
    server_name="firecrawl",
    url=f"https://mcp.firecrawl.dev/{FIRECRAWL_API_KEY}/sse",
)

perplexity_tool_registry = McpToolRegistry.from_stdio_connection(
    server_name="perplexity-ask",
    command="npx",
    args=["-y", "server-perplexity-ask"],
    env={"PERPLEXITY_API_KEY": PERPLEXITY_API_KEY},
)


# # Restrict Portia cloud tools to Firecrawl only
# def include_only_firecrawl(tool) -> bool:
#     return tool.id.startswith(
#         "portia:mcp:custom:mcp.firecrawl.dev:"
#     ) or tool.id.startswith("portia:firecrawl:")


# restricted_registry = PortiaToolRegistry(config=google_config).filter_tools(
#     include_only_firecrawl
# )

portia = Portia(
    config=google_config,
    execution_hooks=CLIExecutionHooks(),
    tools=perplexity_tool_registry + firecrawl_mcp_tool_registry,
)

plan = portia.plan(task)
print(plan.pretty_print())

plan_run = portia.run_plan(plan, end_user=end_user)

print(plan_run.model_dump_json(indent=4))
