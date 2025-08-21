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
import time
from typing import List, Optional
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


#   - version = "black-forest-labs/flux-schnell"
#   - input.num_outputs = 4
#   - input.aspect_ratio = "1:1"
#   - input.output_format = "png"   # Instagram-safe
#   - input.output_quality = 80
#   - input.num_inference_steps = 4
#   - input.go_fast = true
#   - input.disable_safety_checker = false

portia = Portia(
    config=openai_config,
    execution_hooks=CLIExecutionHooks(),
    tools=(
        PortiaToolRegistry(config=openai_config)
        .with_tool_description(
            "portia:mcp:custom:mcp.replicate.com:create_predictions",
            """
            Use this tool to generate video with Replicate's kwaivgi/kling-v1.6-standard model.
            Always include:
              - version = "kwaivgi/kling-v1.6-standard"
              - prompt = user's description
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
              - output: list of video URL strings if present, otherwise null
            MAKE ONLY ONE CALL.
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


class PredictionPollResult(BaseModel):
    status: str
    output: Optional[List[str]] = None


# -------- Plan 1: Generate images --------
user_prompt = input("Enter your video prompt: ")

plan1 = portia.plan(
    f"Generate  video of {user_prompt} using kling-v1.6-standard, with the output in the format of a list of URLs of generated video"
)
print("\n== Plan 1 ==")
print(plan1.pretty_print())

pr1 = portia.run_plan(plan1, structured_output_schema=OutputSpecialId)

print("pr1.outputs.final_output.value", pr1.outputs.final_output.value)


# -------- Poll Replicate prediction until completion and collect URLs --------
def extract_id_and_status(value):
    pred_id = None
    status = None
    # If structured
    try:
        pred_id = getattr(value, "id", None)
        status = getattr(value, "status", None)
        if pred_id and status:
            return pred_id, status
    except Exception:
        pass

    # If dict-like
    if isinstance(value, dict):
        pred_id = value.get("id")
        status = value.get("status")
        if pred_id and status:
            return pred_id, status

    # If string like: id='...' status='...'
    text_val = str(value)
    m_id = re.search(r"id='([^']+)'", text_val)
    m_status = re.search(r"status='([^']+)'", text_val)
    if m_id:
        pred_id = m_id.group(1)
    if m_status:
        status = m_status.group(1)
    return pred_id, status


prediction_id, prediction_status = extract_id_and_status(pr1.outputs.final_output.value)
if not prediction_id:
    raise RuntimeError(
        "Could not determine prediction id from create_predictions result"
    )

print(f"Prediction created: id={prediction_id} status={prediction_status}")

final_urls: List[str] = []
terminal_statuses = {"succeeded", "failed", "canceled", "cancelled"}

while True:
    plan_check = portia.plan(
        f"""
        Call tool 'portia:mcp:custom:mcp.replicate.com:get_predictions' with:
          - id = "{prediction_id}"
        Extract only fields status and output and return exactly:
          {{"status": .status, "output": .output}}
        """
    )
    pr_check = portia.run_plan(
        plan_check, structured_output_schema=PredictionPollResult
    )

    result = pr_check.outputs.final_output.value
    try:
        current_status = result.status
        current_output = result.output
    except Exception:
        # Fallbacks for unexpected shapes
        val = pr_check.outputs.final_output.value
        if isinstance(val, dict):
            current_status = val.get("status")
            current_output = val.get("output")
        else:
            text_val = str(val)
            m_status2 = re.search(
                r"\bstatus\"?[:=]\s*['\"]?([a-zA-Z]+)['\"]?", text_val
            )
            current_status = m_status2.group(1) if m_status2 else None
            current_output = None

    print(f"Poll: status={current_status}")

    if not current_status or current_status.lower() not in terminal_statuses:
        time.sleep(3)
        continue

    if current_status.lower() != "succeeded":
        raise RuntimeError(
            f"Prediction {prediction_id} ended with status {current_status}"
        )

    # Succeeded
    final_urls = current_output or []
    break

print("\nURLs:")
print(json.dumps(final_urls, indent=2))


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


# # Prefer the last step output if present (often contains raw tool output)
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

# # -------- Plan 2: Post to Instagram --------
# plan2 = portia.plan(
#     f"Post the selected image to Instagram with accountId {ACCOUNT_ID} and image_url {chosen_url}"
# )
# print("\n== Plan 2 ==")
# print(plan2.pretty_print())

# pr2 = portia.run_plan(plan2)
# print("\nInstagram Post Result:")
# print(pr2.outputs.final_output.value)
