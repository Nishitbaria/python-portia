from portia import (
    PlanBuilderV2,
    StepOutput,
    Input,
)
from pydantic import BaseModel
from utils.config import portia

# Predefined character URLs
prebuild_character_urls = [
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2PZps4l7vwC1fd4pMXytmhRAYDBUcu3HZNSFo",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2q22n4wMQ9MY3OVAuxjS8dZ04DkcXICptv7Ll",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2FKFMHVtDcfnuGL3wbEeCWSgjrohs1AdYBmRp",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2W5lYjcVc9b4PZyL0KhkgSNCqQzuA2xRfs76F",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2wPrOReDfEB1Ku65aICqL0MmlbczDjp2W47h9",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2OPkTFqCT6b0p92cYIEwxLVH4ay3XtMPFsgDk",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2qFhSZAMQ9MY3OVAuxjS8dZ04DkcXICptv7Ll",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2wMnYa8DfEB1Ku65aICqL0MmlbczDjp2W47h9",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2KUEdHyYhTCsONcWmwFvkrLVfYU43P5AoGMEj",
]


# Pydantic model for product description output
class ProductDescription(BaseModel):
    description: str


class character_url(BaseModel):
    character_url: str


# Final output schema
class FinalOutput(BaseModel):
    character_url: str
    product_url: str
    product_description: str
    dialog: str
    ugc_prediction: dict


def validate_url(url):
    """Basic URL validation"""
    return url.startswith("http://") or url.startswith("https://")


def get_character_url(choice, custom_url=None, prebuild_choice=None):
    """Function to get character URL based on user choice"""
    if choice == "1":  # Custom character
        if not custom_url or not validate_url(custom_url):
            raise ValueError("Invalid custom character URL provided")
        return custom_url
    elif choice == "2":  # Prebuild character
        if not prebuild_choice or not (
            1 <= prebuild_choice <= len(prebuild_character_urls)
        ):
            raise ValueError("Invalid prebuild character choice")
        return prebuild_character_urls[prebuild_choice - 1]
    else:
        raise ValueError("Invalid character choice")


def join_array_to_string(array_output):
    """Join array output from Replicate into single string"""
    if isinstance(array_output, list):
        return " ".join(array_output)
    elif isinstance(array_output, str):
        return array_output
    else:
        return str(array_output)


def extract_and_join_text_content(json_output):
    """Extract and join text content from complex JSON structure"""
    try:
        import json

        if isinstance(json_output, str):
            data = json.loads(json_output)
        else:
            data = json_output

        # Navigate through the JSON structure to find text content
        if isinstance(data, dict):
            if "content" in data and isinstance(data["content"], list):
                text_parts = []
                for item in data["content"]:
                    if isinstance(item, dict) and "text" in item:
                        text_content = item["text"]
                        # Parse the text content if it's a JSON string
                        try:
                            parsed_text = json.loads(text_content)
                            if isinstance(parsed_text, list):
                                text_parts.extend(parsed_text)
                            else:
                                text_parts.append(str(parsed_text))
                        except json.JSONDecodeError:
                            text_parts.append(text_content)
                return " ".join(text_parts)
            elif "text" in data:
                return data["text"]

        # Fallback: convert to string
        return str(json_output)
    except Exception as e:
        # If any error occurs, return the original as string
        return str(json_output)


def pick_first_url(value: object) -> str:
    try:
        import json

        data = value
        if isinstance(value, str):
            try:
                data = json.loads(value)
            except json.JSONDecodeError:
                return value
        if isinstance(data, list) and data:
            return str(data[0])
        if isinstance(data, str):
            return data
        return str(value)
    except Exception:
        return str(value)


def parse_ugc_prediction(raw: object) -> dict:
    """Parse single_tool_agent_step wrapped content into a dict {id, status}.
    Accepts either a dict with content/text, or a JSON string, and returns a dict.
    """
    try:
        # Reuse existing extractor to get inner text if wrapped
        text = extract_and_join_text_content(raw)
        import json
        data = json.loads(text) if isinstance(text, str) else text
        if isinstance(data, dict):
            result = {}
            if "id" in data:
                result["id"] = data["id"]
            if "status" in data:
                result["status"] = data["status"]
            return result
        return {}
    except Exception:
        return {}


def get_dialog_choice():
    """Get user's choice for dialog generation"""
    print("\n=== Dialog Generation ===")
    print("1. Enter custom dialog")
    print("2. Auto generate dialog")

    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice in ["1", "2"]:
            return choice
        print("Invalid choice. Please enter 1 or 2.")


def get_custom_dialog():
    """Get custom dialog from user"""
    print("\n📝 You chose to enter custom dialog")
    while True:
        dialog = input("Enter your custom dialog: ").strip()
        if dialog and len(dialog) > 0:
            return dialog
        print("Dialog cannot be empty. Please enter a valid dialog.")


def extract_id_and_status(result):
    """Extract prediction ID and status from Replicate result"""
    try:
        if isinstance(result, str):
            import json

            data = json.loads(result)
        else:
            data = result

        if isinstance(data, dict):
            prediction_id = data.get("id")
            status = data.get("status")
            return prediction_id, status

        return None, None
    except Exception:
        return None, None


def poll_prediction_until_complete(
    portia, prediction_id, max_attempts=30, delay_seconds=2
):
    """Poll a Replicate prediction until it's complete"""
    import time

    for attempt in range(max_attempts):
        print(f"Polling attempt {attempt + 1}/{max_attempts}...")

        # Create polling plan
        polling_plan = (
            PlanBuilderV2("Poll Replicate prediction")
            .invoke_tool_step(
                tool="portia:mcp:custom:mcp.replicate.com:get_predictions",
                args={
                    "id": prediction_id,
                },
                step_name="get_prediction_status",
            )
            .final_output(output_schema=dict)
            .build()
        )

        # Run polling plan
        polling_run = portia.run_plan(
            polling_plan,
            plan_run_inputs={},
        )

        result = polling_run.outputs.final_output.value

        # Extract status and output
        if isinstance(result, dict):
            status = result.get("status")
            output = result.get("output")

            print(f"Status: {status}")

            if status == "succeeded" and output:
                print("✅ Prediction completed successfully!")
                return output
            elif status in ["failed", "canceled"]:
                print(f"❌ Prediction failed with status: {status}")
                return None
            elif status in ["starting", "processing"]:
                print(f"⏳ Still processing... (status: {status})")
                time.sleep(delay_seconds)
            else:
                print(f"⚠️ Unknown status: {status}")
                time.sleep(delay_seconds)
        else:
            print(f"⚠️ Unexpected result format: {result}")
            time.sleep(delay_seconds)

    print(f"❌ Timed out after {max_attempts} attempts")
    return None


# System prompt for product description
PRODUCT_DESCRIPTION_SYSTEM_PROMPT = """
For Product description Agent:

You are a product describer.

GOAL
Describe only WHAT the product is and HOW it looks. Use visible brand text if clearly readable. Do not add benefits, results, skin types, or claims.

INPUTS
- prompt: may be empty or minimal text
- image: a single product photo

RULES
1) Output EXACTLY 2 lines, each a single sentence. No bullets, no extra lines.
2) Line 1 = Identification: "<Brand> <Category>" if brand text is legible; otherwise "<Category>".
   - Category from obvious cues only (e.g., "glass dropper bottle", "sunscreen tube", "pump bottle"). If unsure, use a neutral container category (e.g., "glass dropper bottle") rather than guessing "serum" or "SPF".
3) Line 2 = Visuals only: material, color, finish, label, cap/closure, shape/size vibes, lighting/background.
4) Never include benefits, ingredients, numbers, SPF, pH, "ideal for…", or claims like hydrates, nourishes, protects, glow, non-greasy, etc.
5) No invented brand names. If none is visible, do not fabricate one.
6) Keep each line concise (~8–16 words). Use commas sparingly; no emojis.

DISALLOWED WORDS (unless explicitly provided as text on pack): hydrates, nourishes, protects, brightens, repairs, SPF, pH-balanced, dermatologist, results, glow, non-greasy, for all skin types, makeup-ready, dewy.

FORMAT
Return only the two lines separated by a single newline.

Example 1 — branded sunscreen tube (brand visible)
	•	Image: cream tube with "Élixir Soin" visible.
Output:
Élixir Soin sunscreen tube.
Matte cream tube with embossed logo, soft-white label, black base, studio light.

Example 2 — unbranded dropper bottle (like your current image)
Output:
Glass dropper bottle.
Frosted semi-opaque bottle with blank white label, silver collar, white pipette cap.

Example 3 — pump bottle with clear brand
Output:
Bundled Hand Wash.
Clear PET pump, black dispenser, minimalist white label, translucent gel, soft daylight backdrop
"""

# System prompt for dialog generation
DIALOG_GENERATION_SYSTEM_PROMPT = """
You are a UGC ad dialogue writer.

GOAL
Write a natural, creator-style dialogue for a short video using ONLY the product description provided in `prompt` (and optional clear visual cues from the image).

INPUTS
- prompt: the product description supplied by the user. It may be plain text OR JSON.
- image (optional): use only obvious visuals (container type/color, label/brand text). If image and prompt conflict, the prompt is the source of truth.

OUTPUT RULES
1) Output EXACTLY 2 sentences on separate lines; speakable in ~10 seconds total (≈18–28 words combined).
2) Sentence 1 = quick hook + brand/product mention (once).
3) Sentence 2 = 1–2 concrete attributes/benefits pulled from the prompt; add a soft CTA only if `include_cta=true`.
4) Do NOT invent claims, numbers, SPF, ingredients, or certifications. No filler like "for all skin types," "pH-balanced," etc., unless explicitly present in the prompt.
5) Keep language simple, first-person creator by default (switch to narrator if `voice="narrator"`). No emojis/hashtags.

PROMPT PARSING
- If plain text, extract brand/product/type/finish/benefits from the text.
- If JSON, read these fields when present:
  {
    "brand": "string",
    "product_name": "string",
    "type": "sunscreen|serum|face wash|...",
    "finish_or_feel": ["lightweight","fast-absorbing","matte","soft glow", ...],
    "key_benefits": ["daily protection","hydrates","softens", ...],
    "notes": ["no white cast","fragrance-free"],
    "voice": "creator|narrator",
    "tone": "casual|luxury-minimal|clinical",
    "include_cta": true|false,
    "cta": "Tap to try|Shop now|Link in bio",
    "language": "en|hi|..."
  }

STYLE
- Friendly UGC tone, concise, present tense. Prefer one texture word + one benefit.
- Brand mention once; keep ~9–14 words per sentence.

FORMAT
Return ONLY the two sentences on separate lines no titles, bullets, or quotes.
"""


def pack_final_output(
    character_url: str,
    product_url: str,
    product_description: str,
    dialog: str,
    ugc_prediction: dict,
) -> dict:
    return {
        "character_url": character_url,
        "product_url": product_url,
        "product_description": product_description,
        "dialog": dialog,
        "ugc_prediction": ugc_prediction,
    }


def extract_avatar_url(result: object, original_url: str, choice: str) -> str:
    """Return final character URL.
    - If choice == "2" (prebuilt), return original_url.
    - Else, try to read URL from result.output (string or first element of list). Fallback to original_url.
    """
    if choice == "2":
        return original_url
    try:
        import json

        data = result
        if isinstance(result, str):
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                return result
        if isinstance(data, dict):
            out = data.get("output")
            if isinstance(out, list) and out:
                return str(out[0])
            if isinstance(out, str) and out:
                return out
        return original_url
    except Exception:
        return original_url


# Build the plan using PlanBuilderV2
plan = (
    PlanBuilderV2("UGC Generator - Character and Product Setup with Replicate")
    .input(
        name="character_choice",
        description="User choice: 1 for custom character, 2 for prebuild characters",
    )
    .input(
        name="custom_character_url",
        description="Custom character URL (required if character_choice is 1)",
        default_value="",
    )
    .input(
        name="prebuild_character_choice",
        description="Prebuild character choice number 1-9 (required if character_choice is 2)",
        default_value=0,
    )
    .input(name="product_url", description="Product image URL")
    .input(
        name="system_prompt",
        description="LLM system prompt",
        default_value=PRODUCT_DESCRIPTION_SYSTEM_PROMPT,
    )
    .input(
        name="dialog_choice",
        description="Dialog choice: 1 for custom dialog, 2 for auto generate",
    )
    .input(
        name="custom_dialog",
        description="Custom dialog (required if dialog_choice is 1)",
        default_value="",
    )
    .input(
        name="dialog_system_prompt",
        description="Dialog generation system prompt",
        default_value=DIALOG_GENERATION_SYSTEM_PROMPT,
    )
    .function_step(
        function=get_character_url,
        args={
            "choice": Input("character_choice"),
            "custom_url": Input("custom_character_url"),
            "prebuild_choice": Input("prebuild_character_choice"),
        },
        step_name="get_character_url",
    )
    .if_(
        condition=lambda choice: choice == "1",
        args={"choice": Input("character_choice")},
    )
    .single_tool_agent_step(
        tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
        task="""
        You MUST call the UGC Avatar Replicate model with EXACT arguments and return ONLY the jq-filtered output.

        Required call:
        - version: 706321a35bebe81c99cb83a6b6db6b1cc0b7281f8da9be48a438de5e0aea3183
        - input.user_image: the provided character URL
        - input.magic_prompt: false
        - input.avatar_preset: "Home Office Avatar"
        - input.debug_mode: true
        - Prefer: wait
        - jq_filter: ".output"

        Do not produce any analysis or text. The step output must be ONLY the jq-filtered result from the tool.
        """,
        inputs=[StepOutput("get_character_url")],
        step_name="avatar_output_raw",
    )
    .function_step(
        function=pick_first_url,
        args={"value": StepOutput("avatar_output_raw")},
        step_name="character_url_generated",
    )
    .else_()
    .function_step(
        function=lambda url: url,
        args={"url": StepOutput("get_character_url")},
        step_name="character_url_prebuilt",
    )
    .endif()
    .function_step(
        function=lambda gen, pre, choice: gen if choice == "1" else pre,
        args={
            "gen": StepOutput("character_url_generated"),
            "pre": StepOutput("character_url_prebuilt"),
            "choice": Input("character_choice"),
        },
        step_name="character_url_final",
    )
    .function_step(
        function=validate_url,
        args={"url": Input("product_url")},
        step_name="validate_product_url",
    )
    .single_tool_agent_step(
        tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
        task="""
        Generate a product description using Claude-4-Sonnet on Replicate. Use the provided system prompt and product image URL to create a detailed product description.
        Always include:
        - version = "anthropic/claude-4-sonnet"
        - input.prompt = "Your Task it To Generate Product description in 2 lines, Brand Name"
        - input.system_prompt = [The detailed system prompt for product description]
        - input.image = [product image URL]
        - jq_filter = ".output"
        - Prefer = "wait"
        """,
        inputs=[Input("product_url"), Input("system_prompt")],
        step_name="generate_product_description",
    )
    .function_step(
        function=extract_and_join_text_content,
        args={"json_output": StepOutput("generate_product_description")},
        step_name="format_product_description",
    )
    .single_tool_agent_step(
        tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
        task="""
        Generate a UGC dialog using Claude-4-Sonnet on Replicate. Use the provided system prompt and product description to create a natural, creator-style dialogue.
        Always include:
        - version = "anthropic/claude-4-sonnet"
        - input.prompt = [The product description from previous step]
        - input.system_prompt = [The dialog generation system prompt]
        - jq_filter = ".output"
        - Prefer = "wait"
        """,
        inputs=[
            StepOutput("format_product_description"),
            Input("dialog_system_prompt"),
        ],
        step_name="generate_auto_dialog",
    )
    .function_step(
        function=extract_and_join_text_content,
        args={"json_output": StepOutput("generate_auto_dialog")},
        step_name="format_auto_dialog",
    )
    .function_step(
        function=lambda auto_dialog, custom_dialog, dialog_choice: (
            auto_dialog if dialog_choice == "2" else custom_dialog
        ),
        args={
            "auto_dialog": StepOutput("format_auto_dialog"),
            "custom_dialog": Input("custom_dialog"),
            "dialog_choice": Input("dialog_choice"),
        },
        step_name="format_dialog",
    )
    .single_tool_agent_step(
        tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
        task="""
        Call the UGC ads generator model with the following inputs:
        - version: 1fb1d9f3ffb5da9774c24ce528c54c916d8d6cd63af866fe2afe85e44fb99999
        - input.avatar_image: The processed character URL (from character_url_final step)
        - input.product_image: The product image URL  
        - input.product_description: The generated product description
        - input.dialogs: The generated or custom dialog
        - input.debug_mode: true
        - Prefer: wait=5
        
        - jq_filter: "{id: .id, status: .status}"
        
        This will generate a UGC video using the provided character, product, description, and dialog.
        """,
        inputs=[
            StepOutput("character_url_final"),
            Input("product_url"),
            StepOutput("format_product_description"),
            StepOutput("format_dialog"),
        ],
        step_name="generate_ugc",
    )
    .function_step(
        function=parse_ugc_prediction,
        args={"raw": StepOutput("generate_ugc")},
        step_name="ugc_prediction_parsed",
    )
    .function_step(
        function=pack_final_output,
        args={
            "character_url": StepOutput("character_url_final"),
            "product_url": Input("product_url"),
            "product_description": StepOutput("format_product_description"),
            "dialog": StepOutput("format_dialog"),
            "ugc_prediction": StepOutput("ugc_prediction_parsed"),
        },
        step_name="pack_final_output",
    )
    .final_output(
        output_schema=FinalOutput,
    )
    .build()
)


def main():
    print("🎬 Welcome to UGC Generator!")
    print("\n=== Character Selection ===")
    print("1. Bring your own character")
    print("2. Use prebuild characters")

    # Get character choice
    while True:
        character_choice = input("\nEnter your choice (1 or 2): ").strip()
        if character_choice in ["1", "2"]:
            break
        print("Invalid choice. Please enter 1 or 2.")

    # Get character details based on choice
    custom_character_url = ""
    prebuild_character_choice = 0

    if character_choice == "1":
        print("\n📝 You chose to bring your own character")
        while True:
            custom_character_url = input("Enter the URL of your character: ").strip()
            if validate_url(custom_character_url):
                break
            print(
                "Invalid URL. Please enter a valid URL starting with http:// or https://"
            )
    else:
        print("\n🎭 You chose to use prebuild characters")
        print("Choose from the following characters:")
        for i, url in enumerate(prebuild_character_urls, 1):
            print(f"{i}. Character {i}")
            print(f"   URL: {url}")

        while True:
            try:
                prebuild_character_choice = int(
                    input(f"\nEnter your choice (1-{len(prebuild_character_urls)}): ")
                )
                if 1 <= prebuild_character_choice <= len(prebuild_character_urls):
                    break
                print(
                    f"Invalid choice. Please enter a number between 1 and {len(prebuild_character_urls)}."
                )
            except ValueError:
                print("Invalid input. Please enter a valid number.")

    # Get product URL
    print("\n=== Product Image ===")
    print("Please provide the URL of your product image.")

    while True:
        product_url = input("\nEnter the product image URL: ").strip()
        if validate_url(product_url):
            break
        print("Invalid URL. Please enter a valid URL starting with http:// or https://")

    # Get dialog choice
    dialog_choice = get_dialog_choice()
    custom_dialog = ""

    if dialog_choice == "1":
        custom_dialog = get_custom_dialog()
        print(f"✅ Custom dialog: {custom_dialog}")
    else:
        print("\n🤖 You chose to auto generate dialog")

    # Prepare inputs for the plan
    plan_inputs = {
        "character_choice": character_choice,
        "custom_character_url": custom_character_url,
        "prebuild_character_choice": prebuild_character_choice,
        "product_url": product_url,
        "dialog_choice": dialog_choice,
        "custom_dialog": custom_dialog,
    }

    # Run the plan
    print("\n🚀 Running Portia plan with Replicate...")
    plan_run = portia.run_plan(plan, plan_run_inputs=plan_inputs)

    # Display results
    print("\n🎉 Plan execution complete!")
    final_output = plan_run.outputs.final_output.value

    # Handle both string and dictionary outputs
    if isinstance(final_output, str):
        print(f"Final Output (string): {final_output}")
        return final_output
    elif isinstance(final_output, dict):
        print(f"Character URL: {final_output.get('character_url', 'N/A')}")
        print(f"Product URL: {final_output.get('product_url', 'N/A')}")
        print(f"Product Description: {final_output.get('product_description', 'N/A')}")
        print(f"Dialog: {final_output.get('dialog', 'N/A')}")

        # Extract UGC prediction ID and status
        ugc_prediction = final_output.get("ugc_prediction", {})
        prediction_id, prediction_status = extract_id_and_status(ugc_prediction)

        if prediction_id:
            print(f"\n🎬 UGC Generation Started:")
            print(f"Prediction ID: {prediction_id}")
            print(f"Status: {prediction_status}")

            # Poll for completion
            print("\n⏳ Polling for UGC generation completion...")
            final_ugc_result = poll_prediction_until_complete(portia, prediction_id)

            if final_ugc_result:
                print("\n✅ UGC Generation Complete!")
                print("Final UGC Result:")
                print(final_ugc_result)
            else:
                print("\n❌ UGC Generation failed or timed out")
        else:
            print("\n❌ Could not extract prediction ID from UGC generation result")

        return final_output
    else:
        print(f"Final Output (unknown type): {final_output}")
        return final_output


if __name__ == "__main__":
    result = main()
