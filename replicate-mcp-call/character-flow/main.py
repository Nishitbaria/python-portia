from portia import PlanBuilderV2
from portia.builder.reference import StepOutput, Input
from pydantic import BaseModel
from utils.config import portia
import json


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


class DialogOutput(BaseModel):
    dialog: str


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


# def extract_and_join_text_content(json_output):
#     """Extract and join text content from complex JSON structure"""
#     try:
#         import json

#         if isinstance(json_output, str):
#             data = json.loads(json_output)
#         else:
#             data = json_output

#         # Navigate through the JSON structure to find text content
#         if isinstance(data, dict):
#             # Check for the wrapped structure from single_tool_agent_step
#             if "content" in data and isinstance(data["content"], list):
#                 text_parts = []
#                 for item in data["content"]:
#                     if isinstance(item, dict) and "text" in item:
#                         text_content = item["text"]
#                         # Parse the text content if it's a JSON string
#                         try:
#                             parsed_text = json.loads(text_content)
#                             if isinstance(parsed_text, list):
#                                 # Filter out empty strings and join
#                                 filtered_parts = [
#                                     str(part)
#                                     for part in parsed_text
#                                     if part and str(part).strip()
#                                 ]
#                                 text_parts.extend(filtered_parts)
#                             else:
#                                 text_parts.append(str(parsed_text))
#                         except json.JSONDecodeError:
#                             # If not JSON, treat as plain text
#                             if text_content.strip():
#                                 text_parts.append(text_content)
#                 return " ".join(text_parts)
#             elif "text" in data:
#                 return data["text"]
#             elif "output" in data:
#                 # Direct output field
#                 output = data["output"]
#                 if isinstance(output, list):
#                     return " ".join([str(item) for item in output if item])
#                 return str(output)

#         # Fallback: convert to string
#         return str(json_output)
#     except Exception as e:
#         print(f"Error extracting text content: {e}")
#         # If any error occurs, return the original as string
#         return str(json_output)


def extract_and_join_text_content(json_output):
    """Extract and join text content from complex JSON structure"""
    print(f"[DEBUG] Input json_output type: {type(json_output)}")
    print(f"[DEBUG] Input json_output: {json_output}")
    print(f"[DEBUG] Function called with: {json_output}")

    try:
        print("Extracting and joining text content", json_output)

        if isinstance(json_output, str):
            print("[DEBUG] Input is string, parsing JSON...")
            data = json.loads(json_output)
            print(f"[DEBUG] Parsed data type: {type(data)}")
        else:
            print("[DEBUG] Input is not string, using as-is")
            data = json_output
            print(f"[DEBUG] Data type: {type(data)}")

        # Navigate through the JSON structure to find text content
        if isinstance(data, dict):
            print(f"[DEBUG] Data is dict with keys: {list(data.keys())}")

            if "content" in data and isinstance(data["content"], list):
                print(f"[DEBUG] Found 'content' list with {len(data['content'])} items")
                text_parts = []
                for i, item in enumerate(data["content"]):
                    print(f"[DEBUG] Processing content item {i}: {type(item)} - {item}")
                    if isinstance(item, dict) and "text" in item:
                        text_content = item["text"]
                        print(f"[DEBUG] Found 'text' in item {i}: {text_content}")
                        # Parse the text content if it's a JSON string
                        try:
                            parsed_text = json.loads(text_content)
                            print(
                                f"[DEBUG] Successfully parsed text as JSON: {type(parsed_text)} - {parsed_text}"
                            )
                            if isinstance(parsed_text, list):
                                # Join the array of strings into a single string
                                joined_text = "".join(parsed_text)
                                print(
                                    f"[DEBUG] Joined array into string: {joined_text}"
                                )
                                text_parts.append(joined_text)
                                print(
                                    f"[DEBUG] Added joined text to text_parts, current length: {len(text_parts)}"
                                )
                            else:
                                text_parts.append(str(parsed_text))
                                print(
                                    f"[DEBUG] Added string to text_parts, current length: {len(text_parts)}"
                                )
                        except json.JSONDecodeError as e:
                            print(f"[DEBUG] JSON decode error for text content: {e}")
                            text_parts.append(text_content)
                            print(
                                f"[DEBUG] Added raw text to text_parts, current length: {len(text_parts)}"
                            )
                    else:
                        print(f"[DEBUG] Item {i} is not a dict with 'text' key")

                result = " ".join(text_parts)
                print(f"[DEBUG] Final result from content list: {result}")
                print(f"[OUTPUT] {result}")
                return result
            elif "text" in data:
                print(f"[DEBUG] Found 'text' key directly in data: {data['text']}")
                print(f"[OUTPUT] {data['text']}")
                return data["text"]
            else:
                print("[DEBUG] No 'content' list or 'text' key found in dict")

        # Fallback: convert to string
        print(f"[DEBUG] Using fallback - converting to string: {str(json_output)}")
        print(f"[OUTPUT] {str(json_output)}")
        return str(json_output)
    except Exception as e:
        # If any error occurs, return the original as string
        print(f"[DEBUG] Exception occurred: {e}")
        print(f"[DEBUG] Returning original as string: {str(json_output)}")
        print(f"[OUTPUT] {str(json_output)}")
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
        # Handle the complex nested structure from single_tool_agent_step
        if isinstance(raw, dict):
            # Check if it's the wrapped structure
            if "content" in raw and isinstance(raw["content"], list):
                for item in raw["content"]:
                    if isinstance(item, dict) and "text" in item:
                        try:
                            data = json.loads(item["text"])
                            if isinstance(data, dict):
                                result = {}
                                if "id" in data:
                                    result["id"] = data["id"]
                                if "status" in data:
                                    result["status"] = data["status"]
                                return result
                        except json.JSONDecodeError:
                            continue
            # Direct dict with id/status
            elif "id" in raw or "status" in raw:
                result = {}
                if "id" in raw:
                    result["id"] = raw["id"]
                if "status" in raw:
                    result["status"] = raw["status"]
                return result

        # Try as string
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    result = {}
                    if "id" in data:
                        result["id"] = data["id"]
                    if "status" in data:
                        result["status"] = data["status"]
                    return result
            except json.JSONDecodeError:
                pass

        return {}
    except Exception as e:
        print(f"Error parsing UGC prediction: {e}")
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


def extract_id_and_status(value):
    """Robustly extract prediction id and status from various shapes.

    Handles:
    - dicts with id/status
    - strings containing JSON
    - single_tool_agent_step wrapped dict: { content: [{ text: "{\"id\":..., \"status\":...}" }] }
    - fallback regex over string representation
    """
    import json, re

    print(f"[DEBUG] extract_id_and_status input type: {type(value)}")
    print(f"[DEBUG] extract_id_and_status input value: {value}")

    # 1) Wrapped structure from single_tool_agent_step
    try:
        print(f"[DEBUG] Checking if wrapped structure...")
        if (
            isinstance(value, dict)
            and "content" in value
            and isinstance(value["content"], list)
        ):
            print(
                f"[DEBUG] Found wrapped structure with {len(value['content'])} content items"
            )
            for i, item in enumerate(value["content"]):
                print(f"[DEBUG] Content item {i}: {item}")
                if isinstance(item, dict) and "text" in item:
                    print(f"[DEBUG] Found text in item {i}: {item['text']}")
                    try:
                        inner = json.loads(item["text"])
                        print(f"[DEBUG] Parsed inner JSON: {inner}")
                        if isinstance(inner, dict):
                            pred_id = inner.get("id")
                            status = inner.get("status")
                            print(
                                f"[DEBUG] Extracted pred_id={pred_id}, status={status}"
                            )
                            if pred_id or status:
                                print(f"[DEBUG] Returning: ({pred_id}, {status})")
                                return pred_id, status
                    except json.JSONDecodeError as e:
                        print(f"[DEBUG] JSON decode error: {e}")
                        continue
    except Exception as e:
        print(f"[DEBUG] Exception in wrapped structure check: {e}")
        pass

    # 2) Direct dict
    try:
        if isinstance(value, dict):
            pred_id = value.get("id")
            status = value.get("status")
            if pred_id or status:
                return pred_id, status
    except Exception:
        pass

    # 3) String → JSON
    try:
        if isinstance(value, str):
            try:
                data = json.loads(value)
                if isinstance(data, dict):
                    pred_id = data.get("id")
                    status = data.get("status")
                    if pred_id or status:
                        return pred_id, status
            except json.JSONDecodeError:
                pass
    except Exception:
        pass

    # 4) Fallback: regex over string form
    try:
        text_val = str(value)
        print(f"[DEBUG] Trying regex fallback on: {text_val}")
        m_id = re.search(r"\bid\"?[:=]\s*['\"]?([a-zA-Z0-9_-]{8,})", text_val)
        m_status = re.search(r"\bstatus\"?[:=]\s*['\"]?([a-zA-Z]+)", text_val)
        pred_id = m_id.group(1) if m_id else None
        status = m_status.group(1) if m_status else None
        print(f"[DEBUG] Regex extracted pred_id={pred_id}, status={status}")
        return pred_id, status
    except Exception as e:
        print(f"[DEBUG] Exception in regex fallback: {e}")
        print(f"[DEBUG] Final fallback: returning (None, None)")
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
            .final_output(output_schema=PredictionStatus)
            .build()
        )

        # Run polling plan
        polling_run = portia.run_plan(
            polling_plan,
            plan_run_inputs={},
        )

        result = polling_run.outputs.final_output.value

        # Extract status and output from Pydantic model
        if hasattr(result, 'status') and hasattr(result, 'output'):
            status = result.status
            output = result.output
        elif isinstance(result, dict):
            status = result.get("status")
            output = result.get("output")
        else:
            print(f"⚠️ Unexpected result format: {result}")
            time.sleep(delay_seconds)
            continue

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
6) Keep each line concise (~8-16 words). Use commas sparingly; no emojis.

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
3) Sentence 2 = 1-2 concrete attributes/benefits pulled from the prompt; add a soft CTA only if `include_cta=true`.
4) Do NOT invent claims, numbers, SPF, ingredients, or certifications. No filler like "for all skin types," "pH-balanced," etc., unless explicitly present in the prompt.
5) Keep language simple, first-person creator by default (switch to narrator if `voice="narrator"`). No emojis/hashtags.

PROMPT PARSING
- If plain text, extract brand/product/type/finish/benefits from the text.
- IF JSON then extract the text field from the content array of the first element
- Example 
STYLE
- Friendly UGC tone, concise, present tense. Prefer one texture word + one benefit.
- Brand mention once; keep ~9-14 words per sentence.

FORMAT
Return ONLY the two sentences on separate lines no titles, bullets, or quotes.
"""


def join_array_to_string(array_output):
    """Join array output from Replicate into single string"""
    if isinstance(array_output, list):
        return " ".join(array_output)
    elif isinstance(array_output, str):
        return array_output
    else:
        return str(array_output)


def pack_final_output(
    character_url: str,
    product_url: str,
    product_description: str,
    dialog: str,
    ugc_prediction,
) -> dict:
    # Extract ID and status from the raw ugc_prediction response
    print(
        f"[PACK DEBUG] Received ugc_prediction: {ugc_prediction} (type: {type(ugc_prediction)})"
    )
    prediction_id, status = extract_id_and_status(ugc_prediction)
    print(f"[PACK DEBUG] Extracted prediction_id={prediction_id}, status={status}")

    return {
        "character_url": character_url,
        "product_url": product_url,
        "product_description": product_description,
        "dialog": dialog,
        "ugc_prediction": {
            "id": prediction_id,
            "status": status,
        },
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


class UGC_Prediction(BaseModel):
    """UGC Prediction model"""

    product_description: str
    dialog: str
    character_url: str
    product_url: str
    id: str
    status: str


class PredictionStatus(BaseModel):
    """Model for prediction status polling"""
    status: str
    output: list = None


def extract_id_and_status_vinayak_way(raw):
    print("Vinayak", raw)
    print("Vinayak", type(raw))
    textObject = raw["content"][0]["text"]
    print("Vinayak", textObject)
    print("Vinayak", type(textObject))
    textObject = json.loads(textObject)
    print("Vinayak", textObject)
    print("Vinayak", type(textObject))
    print("Vinayak", textObject["id"])
    print("Vinayak", textObject["status"])
    print("Vinayak", textObject["id"], textObject["status"])
    return textObject


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
        CRITICAL: You MUST include ALL required parameters in your tool call.

        Call the tool with this EXACT structure:
        {
          "version": "openai/gpt-4o",
          "input": {
            "prompt": "Write Prompt for this product",
            "system_prompt": [use the system_prompt input],
            "image_input": [[use the product_url input]]
          },
          "jq_filter": ".output",
          "Prefer": "wait"
        }

        DO NOT OMIT THE "version" FIELD. It is required and must be "openai/gpt-4o".
        THE Image input must be a list with the product url as the first element.
        
        IMPORTANT: Extract the product description text from the array output and return it in this format:
        {
          "description": "product description text here"
        }
        """,
        inputs=[Input("product_url"), Input("system_prompt")],
        step_name="generate_product_description",
        output_schema=ProductDescription,
    )
    .single_tool_agent_step(
        tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
        task="""
        You need to generate the final dialog based on the user's choice:
        
        If dialog_choice is "2" (auto generate dialog):
        - Call GPT-4o with this structure:
        {
          "version": "openai/gpt-4o",
          "input": {
            "prompt": [use the generate_product_description.description output],
            "system_prompt": [use the dialog_system_prompt input]
          },
          "jq_filter": ".output",
          "Prefer": "wait"
        }
        - Extract the dialog text from the array output
        
        If dialog_choice is "1" (custom dialog):
        - Simply return the custom_dialog input as-is
        
        IMPORTANT: Return the final dialog text in this format:
        {
          "dialog": "final dialog text here"
        }
        DO NOT OMIT THE "version" FIELD when calling GPT-4o. It is required and must be "openai/gpt-4o".
        """,
        inputs=[
            StepOutput("generate_product_description"),
            Input("dialog_system_prompt"),
            Input("dialog_choice"),
            Input("custom_dialog"),
        ],
        step_name="generate_final_dialog",
        output_schema=DialogOutput,
    )
    .single_tool_agent_step(
        tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
        task="""
        CRITICAL: You MUST include ALL required parameters in your tool call with the EXACT mapping specified below.
        
        IMPORTANT: Do NOT mix up product_description and dialogs parameters. They are different:
        - product_description: Should contain the formatted product description (what the product IS and how it LOOKS)
        - dialogs: Should contain the dialog text (what the person SAYS in the video)

        Call the tool with this EXACT structure and parameter mapping:
        {
          "version": "1fb1d9f3ffb5da9774c24ce528c54c916d8d6cd63af866fe2afe85e44fb99999",
          "input": {
            "avatar_image": [use the character_url_final output - this is the character/avatar image URL],
            "product_image": [use the product_url input - this is the product image URL],
            "product_description": [use the generate_product_description.description output - this describes what the product is and looks like],
            "dialogs": [use the generate_final_dialog.dialog output - this is what the person says in the video],
            "debug_mode": true
          },
          "jq_filter": "{id: .id, status: .status}",
          "Prefer": "wait=5"
        }
                
        DO NOT OMIT THE "version" FIELD. It is required.
        DOUBLE CHECK: product_description gets the product description, dialogs gets the dialog text.
        """,
        inputs=[
            StepOutput("character_url_final"),
            Input("product_url"),
            StepOutput("generate_product_description"),
            StepOutput("generate_final_dialog"),
        ],
        step_name="generate_ugc",
    )
    .llm_step(
        task="""
        You will receive the output from the previous step which contains the UGC generation response.
        
        The response will be in this format:
        {"meta":null,"content":[{"type":"text","text":"{\\"id\\":\\"ej30c7shdxrme0crv0pr0fm8ag\\",\\"status\\":\\"starting\\"}"}]}
        
        Your task is to:
        1. Extract the JSON from content[0].text
        2. Parse it to get the id and status
        3. Create a structured object with ALL these fields:
           - product_description: [use the generate_product_description.description output]
           - dialog: [use the generate_final_dialog.dialog output] 
           - character_url: [use the character_url_final output]
           - product_url: [use the product_url input]
           - id: [extracted from the UGC response]
           - status: [extracted from the UGC response]
        
        Return ONLY the structured object with these 6 fields.
        """,
        inputs=[
            StepOutput("generate_ugc"),
            StepOutput("generate_product_description"),
            StepOutput("generate_final_dialog"),
            StepOutput("character_url_final"),
            Input("product_url"),
        ],
        step_name="pack_final_output_llm",
        output_schema=UGC_Prediction,
    )
    .final_output(
        output_schema=UGC_Prediction,
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
    print(f"Raw final output: {final_output}")
    print(f"Final output type: {type(final_output)}")

    # Extract prediction ID and status from structured output
    if hasattr(final_output, "id") and hasattr(final_output, "status"):
        # Pydantic model with id and status attributes
        prediction_id = final_output.id
        prediction_status = final_output.status
    elif isinstance(final_output, dict):
        # Dict with id and status keys
        prediction_id = final_output.get("id")
        prediction_status = final_output.get("status")
    else:
        # Fallback: try to extract from string representation
        prediction_id, prediction_status = extract_id_and_status(final_output)

    print(f"Extracted prediction_id: {prediction_id}")
    print(f"Extracted prediction_status: {prediction_status}")

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
        print(f"Final output object: {final_output}")

    return final_output


if __name__ == "__main__":
    result = main()
