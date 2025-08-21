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
            Use this tool to generate images with Replicate's Flux-Schnell model.
            Always include:
              - model = "kwaivgi/kling-v1.6-standard"
              - prompt = user's description
            Always set Prefer = "wait".
            Extract and return the list of image URLs using jq_filter = .output
            """,
        )
        .with_tool_description(
            "portia:mcp:custom:us2.make.com:s2795860_integration_instagram_for_business_facebook_log",
            f"""
            Use this tool to post an image to Instagram with accountId {ACCOUNT_ID}.
            """,
        )
    ),
)


class OutputUrlList(BaseModel):
    urls: list[str]


# -------- Plan 1: Generate images --------
user_prompt = input("Enter your image prompt: ")

plan1 = portia.plan(
    f"Generate 4 images of {user_prompt} using flux-schnell, with the output in the format of a list of URLs of generated images"
)
print("\n== Plan 1 ==")
print(plan1.pretty_print())

pr1 = portia.run_plan(plan1, structured_output_schema=OutputUrlList)

print("pr1.outputs.final_output.value", pr1.outputs.final_output.value)


# def extract_urls(value):

#     url_pattern = r'https://[^\s"\]]+\.(?:png|jpg|jpeg|webp)'

#     # Case: already a list of URLs
#     if isinstance(value, list):
#         if all(isinstance(x, str) and x.startswith("http") for x in value):
#             return value
#         # Fallthrough: attempt to find URLs within list items
#         text = "\n".join(str(x) for x in value)
#         return re.findall(url_pattern, text)

#     # Case: dict with content/text (Portia Output shape)
#     if isinstance(value, dict):
#         if (
#             "content" in value
#             and isinstance(value["content"], list)
#             and value["content"]
#         ):
#             first = value["content"][0]
#             if isinstance(first, dict) and "text" in first:
#                 text_val = first["text"]
#                 try:
#                     parsed = json.loads(text_val)
#                     return extract_urls(parsed)
#                 except json.JSONDecodeError:
#                     return re.findall(url_pattern, text_val)
#         # Fallback: scan dict as text
#         return re.findall(url_pattern, json.dumps(value))

#     # Case: string
#     if isinstance(value, str):
#         # Try JSON first
#         try:
#             parsed = json.loads(value)
#             return extract_urls(parsed)
#         except json.JSONDecodeError:
#             return re.findall(url_pattern, value)

#     # Fallback: stringify and scan
#     return re.findall(url_pattern, str(value))


# Prefer the last step output if present (often contains raw tool output)
# raw_output = None
# if pr1.outputs.step_outputs:
#     last_output_obj = list(pr1.outputs.step_outputs.values())[-1]
#     # Output object exposes get_value() which returns the stored value
#     try:
#         raw_output = last_output_obj.get_value()
#     except Exception:
#         raw_output = getattr(last_output_obj, "value", None)
# else:
#     raw_output = pr1.outputs.final_output.value

# urls = extract_urls(raw_output)

# # If we still don't have URLs, try the summarized final output text
# if not urls:
#     urls = extract_urls(pr1.outputs.final_output.value)

# print(f"\nFound {len(urls)} image URLs:")
# for i, u in enumerate(urls, 1):
#     print(f"{i}. {u}")

# if not urls:
#     print("No image URLs found in the output!")
#     exit(1)

# choice = int(input(f"Choose an image [1-{len(urls)}]: ").strip())
# chosen_url = urls[choice - 1]
# print(f"\nYou chose: {chosen_url}")

# -------- Plan 2: Post to Instagram --------
# plan2 = portia.plan(
#     f"Post the selected image to Instagram with accountId {ACCOUNT_ID} and image_url {chosen_url}"
# )
# print("\n== Plan 2 ==")
# print(plan2.pretty_print())

# pr2 = portia.run_plan(plan2)
# print("\nInstagram Post Result:")
# print(pr2.outputs.final_output.value)
