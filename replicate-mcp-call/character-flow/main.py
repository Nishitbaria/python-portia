from portia import (
    PlanBuilderV2,
    StepOutput,
    Input,
)

import json

prebuild_character_url = [
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


def validate_url(url):
    """Basic URL validation"""
    return url.startswith("http://") or url.startswith("https://")


def get_character_choice():
    """Get user's choice between own character or prebuild characters"""
    print("\n=== Character Selection ===")
    print("1. Bring your own character")
    print("2. Use prebuild characters")

    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice in ["1", "2"]:
            return choice
        print("Invalid choice. Please enter 1 or 2.")


def get_custom_character_url():
    """Get custom character URL from user with validation"""
    while True:
        url = input("\nEnter the URL of your character: ").strip()
        if validate_url(url):
            return url
        print("Invalid URL. Please enter a valid URL starting with http:// or https://")


def select_prebuild_character():
    """Let user select from prebuild character URLs"""
    print("\n=== Prebuild Characters ===")
    print("Choose from the following characters:")

    for i, url in enumerate(prebuild_character_url, 1):
        print(f"{i}. Character {i}")
        print(f"   URL: {url}")

    while True:
        try:
            choice = int(
                input(f"\nEnter your choice (1-{len(prebuild_character_url)}): ")
            )
            if 1 <= choice <= len(prebuild_character_url):
                selected_url = prebuild_character_url[choice - 1]
                print(f"\nSelected character: {selected_url}")
                return selected_url
            else:
                print(
                    f"Invalid choice. Please enter a number between 1 and {len(prebuild_character_url)}."
                )
        except ValueError:
            print("Invalid input. Please enter a valid number.")


def get_product_url():
    """Get product image URL from user with validation"""
    print("\n=== Product Image ===")
    print("Please provide the URL of your product image.")

    while True:
        url = input("\nEnter the product image URL: ").strip()
        if validate_url(url):
            return url
        print("Invalid URL. Please enter a valid URL starting with http:// or https://")


def main():
    print("🎬 Welcome to UGC Generator!")

    # Step 1: Get character choice
    character_choice = get_character_choice()

    # Step 2: Get character URL based on choice
    if character_choice == "1":
        print("\n📝 You chose to bring your own character")
        character_url = get_custom_character_url()
        print(f"✅ Custom character URL: {character_url}")
    else:
        print("\n🎭 You chose to use prebuild characters")
        character_url = select_prebuild_character()
        print(f"✅ Selected prebuild character: {character_url}")

    # Step 3: Get product image URL
    product_url = get_product_url()
    print(f"✅ Product image URL: {product_url}")

    # For now, return both URLs
    # This will be extended with the full flow later
    return {"character_url": character_url, "product_url": product_url}


if __name__ == "__main__":
    result = main()
    print(f"\n🎉 Setup complete!")
    print(f"Character URL: {result['character_url']}")
    print(f"Product URL: {result['product_url']}")
