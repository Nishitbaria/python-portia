from portia.builder import PlanBuilderV2, StepOutput, Input
from portia import (
    Config,
    DefaultToolRegistry,
    LLMProvider,
    Portia,
    PortiaToolRegistry,
    StorageClass,
    LogLevel,
)
from portia.cli import CLIExecutionHooks
from dotenv import load_dotenv
import os

load_dotenv()

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

# Setup Portia configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_config = Config.from_default(
    llm_provider=LLMProvider.OPENAI,
    default_model="openai/gpt-4o",
    openai_api_key=OPENAI_API_KEY,
    storage_class=StorageClass.CLOUD,
    log_level=LogLevel.INFO,
)

registry = PortiaToolRegistry(config=openai_config)

portia = Portia(
    config=openai_config,
    execution_hooks=CLIExecutionHooks(),
    tools=registry,
)


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


def get_product_description(product_url, character_url):
    """Placeholder function for product description generation"""
    # This will be replaced with actual LLM call later
    return f"Product description for {product_url} with character {character_url}"


# Build the plan using PlanBuilderV2
plan = (
    PlanBuilderV2("UGC Generator - Character and Product Setup")
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
    .function_step(
        function=get_product_description,
        args={
            "product_url": Input("product_url"),
            "character_url": StepOutput("get_character_url"),
        },
        step_name="generate_product_description",
    )
    .final_output(
        output_schema={
            "character_url": str,
            "product_url": str,
            "product_description": str,
        },
        summarize=True,
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
    print("\n🚀 Running Portia plan...")
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
