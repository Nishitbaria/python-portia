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


# Final output schema
class FinalOutput(BaseModel):
    character_url: str
    product_url: str
    product_description: str


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


def pack_final_output(
    character_url: str, product_url: str, product_description: str
) -> dict:
    return {
        "character_url": character_url,
        "product_url": product_url,
        "product_description": product_description,
    }


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
    .function_step(
        function=get_character_url,
        args={
            "choice": Input("character_choice"),
            "custom_url": Input("custom_character_url"),
            "prebuild_choice": Input("prebuild_character_choice"),
        },
        step_name="get_character_url",
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
        - input.prompt = "Write Prompt for this product"
        - input.system_prompt = [The detailed system prompt for product description]
        - input.image = [product image URL]
        - jq_filter = ".output"
        - Prefer = "wait"
        """,
        inputs=[Input("product_url"), Input("system_prompt")],
        step_name="generate_product_description",
    )
    .function_step(
        function=join_array_to_string,
        args={"array_output": StepOutput("generate_product_description")},
        step_name="format_product_description",
    )
    .function_step(
        function=pack_final_output,
        args={
            "character_url": StepOutput("get_character_url"),
            "product_url": Input("product_url"),
            "product_description": StepOutput("format_product_description"),
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

    # Prepare inputs for the plan
    plan_inputs = {
        "character_choice": character_choice,
        "custom_character_url": custom_character_url,
        "prebuild_character_choice": prebuild_character_choice,
        "product_url": product_url,
    }

    # Run the plan
    print("\n🚀 Running Portia plan with Replicate...")
    plan_run = portia.run_plan(plan, plan_run_inputs=plan_inputs)

    # Display results
    print("\n🎉 Plan execution complete!")
    final_output = plan_run.outputs.final_output.value
    print(f"Character URL: {final_output['character_url']}")
    print(f"Product URL: {final_output['product_url']}")
    print(f"Product Description: {final_output['product_description']}")

    return final_output


if __name__ == "__main__":
    result = main()
