import os, json
from dotenv import load_dotenv
from portia import (
    Config,
    LLMProvider,
    Portia,
    PortiaToolRegistry,
    StorageClass,
    LogLevel,
    PlanBuilderV2,
    StepOutput,
    Input,
    MultipleChoiceClarification,
    InputClarification,
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


class OutputSpecialId(BaseModel):
    id: str
    status: str


class PredictionPollResult(BaseModel):
    status: str
    output: Optional[List[str]] = None


class CaptionGenerationResult(BaseModel):
    caption: str
    tweet_text: Optional[str] = None


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


# -------- Plan 1: Generate images --------
user_prompt = input("Enter your image prompt: ")

plan1 = portia.plan(
    f"Generate images of {user_prompt} using flux-schnell, with the output in the format of a list of URLs of generated images"
)
print("\n== Plan 1 ==")
print(plan1.pretty_print())

pr1 = portia.run_plan(plan1, structured_output_schema=OutputSpecialId)

print("pr1.outputs.final_output.value", pr1.outputs.final_output.value)

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

# -------- Plan 2: Social Media Posting Flow --------
if final_urls:
    # Let user choose which image to use
    print(f"\nGenerated {len(final_urls)} images:")
    for i, url in enumerate(final_urls, 1):
        print(f"{i}. {url}")

    while True:
        try:
            choice = int(
                input(f"\nChoose an image to post [1-{len(final_urls)}]: ").strip()
            )
            if 1 <= choice <= len(final_urls):
                chosen_url = final_urls[choice - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(final_urls)}")
        except ValueError:
            print("Please enter a valid number")

    # Ask user for posting preferences
    print(f"\nImage selected successfully! URL: {chosen_url}")

    # Use clarification to get posting preferences
    posting_plan = portia.plan(
        f"""
        Ask the user where they want to post the image: Instagram, Twitter, or both.
        The image URL is: {chosen_url}
        The original prompt was: {user_prompt}
        """
    )

    posting_run = portia.run_plan(posting_plan)

    # Handle clarifications for posting preferences
    while posting_run.state == "NEED_CLARIFICATION":
        clarifications = posting_run.get_outstanding_clarifications()
        for clarification in clarifications:
            if isinstance(clarification, MultipleChoiceClarification):
                print(f"\n{clarification.user_guidance}")
                print("Options:")
                for i, option in enumerate(clarification.options, 1):
                    print(f"{i}. {option}")
                choice = input("Enter your choice (1, 2, 3, etc.): ").strip()
                try:
                    selected_option = clarification.options[int(choice) - 1]
                    posting_run = portia.resolve_clarification(
                        clarification, selected_option, posting_run
                    )
                except (ValueError, IndexError):
                    print("Invalid choice. Please try again.")
            elif isinstance(clarification, InputClarification):
                print(f"\n{clarification.user_guidance}")
                user_input = input("Enter your response: ").strip()
                posting_run = portia.resolve_clarification(
                    clarification, user_input, posting_run
                )

        posting_run = portia.resume(posting_run)

    # Extract posting preference from the run
    posting_preference = posting_run.outputs.final_output.value.lower()

    # Determine channels based on user preference
    if "instagram" in posting_preference and "twitter" in posting_preference:
        channels = "both"
    elif "instagram" in posting_preference:
        channels = "instagram"
    elif "twitter" in posting_preference:
        channels = "twitter"
    else:
        print("Could not determine posting preference. Defaulting to Instagram.")
        channels = "instagram"

    print(f"\nPosting to: {channels}")

    # Generate caption using PlanBuilderV2
    caption_plan = (
        PlanBuilderV2(
            f"Generate engaging social media captions for an image about {user_prompt}"
        )
        .input(name="image_url", description="The URL of the generated image")
        .input(
            name="original_prompt",
            description="The original prompt used to generate the image",
        )
        .input(
            name="channels", description="Where to post: instagram, twitter, or both"
        )
        .llm_step(
            task=f"""
            Generate engaging social media captions for an image.
            
            Image URL: {chosen_url}
            Original prompt: {user_prompt}
            Posting to: {channels}
            
            Create:
            1. An Instagram caption (engaging, descriptive, with relevant hashtags)
            2. A Twitter post text (shorter, punchy, within character limits)
            
            Make them engaging, relevant to the image content, and appropriate for each platform.
            Use emojis where appropriate but don't overdo it.
            """,
            inputs=[Input("image_url"), Input("original_prompt"), Input("channels")],
            output_schema=CaptionGenerationResult,
            step_name="generate_captions",
        )
        .final_output(output_schema=CaptionGenerationResult)
        .build()
    )

    caption_run = portia.run_plan(
        caption_plan,
        plan_run_inputs={
            "image_url": chosen_url,
            "original_prompt": user_prompt,
            "channels": channels,
        },
    )

    generated_caption = caption_run.outputs.final_output.value.caption
    generated_tweet = (
        caption_run.outputs.final_output.value.tweet_text or generated_caption
    )

    print(f"\nGenerated Instagram Caption:")
    print(generated_caption)
    if channels in ["twitter", "both"]:
        print(f"\nGenerated Tweet Text:")
        print(generated_tweet)

    # Validate caption with user
    while True:
        validation_choice = (
            input("\nDo you want to use this caption? (yes/no/regenerate): ")
            .strip()
            .lower()
        )

        if validation_choice in ["yes", "y"]:
            break
        elif validation_choice in ["no", "n"]:
            print("Caption rejected. Exiting without posting.")
            exit(0)
        elif validation_choice in ["regenerate", "r"]:
            # Regenerate caption
            caption_run = portia.run_plan(
                caption_plan,
                plan_run_inputs={
                    "image_url": chosen_url,
                    "original_prompt": user_prompt,
                    "channels": channels,
                },
            )

            generated_caption = caption_run.outputs.final_output.value.caption
            generated_tweet = (
                caption_run.outputs.final_output.value.tweet_text or generated_caption
            )

            print(f"\nNew Generated Instagram Caption:")
            print(generated_caption)
            if channels in ["twitter", "both"]:
                print(f"\nNew Generated Tweet Text:")
                print(generated_tweet)
        else:
            print("Please enter 'yes', 'no', or 'regenerate'")

    # Post to social media
    print(f"\nPosting to {channels}...")

    posting_payload = {
        "channels": channels,
        "caption": generated_caption,
        "tweet_text": generated_tweet if channels in ["twitter", "both"] else "",
        "image_url": chosen_url,
    }

    social_plan = portia.plan(
        f"""
        Post the image to social media using the Make.com integration.
        
        Payload:
        {json.dumps(posting_payload, indent=2)}
        
        Use the tool 'portia:mcp:custom:us2.make.com:s2795860_mcp_social_post_ig_x_both'
        with the exact payload above.
        """
    )

    social_run = portia.run_plan(social_plan)
    print("\nSocial Media Post Result:")
    print(social_run.outputs.final_output.value)

else:
    print("No image URLs generated. Cannot proceed with social media posting.")
