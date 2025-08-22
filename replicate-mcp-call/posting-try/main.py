from portia import (
    PlanBuilderV2,
    StepOutput,
    Input,
)
from utils.config import portia
from utils.schema import PostingResult, OutputSpecialId
from utils.utils_function import (
    handle_outstanding_clarifications,
    safe_final_value,
    extract_id_and_status,
    poll_prediction_until_complete,
    build_image_generation_plan,
)
import json


def main():
    """Main workflow for image generation and social media posting."""

    # Step 1: Get user input for image prompt
    print("=== AI Image Generator + Social Media Poster ===")
    user_prompt = input("Enter your image prompt: ").strip()

    if not user_prompt:
        print("No prompt provided. Exiting.")
        return

    print(f"\nGenerating images for: {user_prompt}")

    # Step 2: Generate images using Replicate
    print("\n=== Image Generation ===")
    image_generation_plan = build_image_generation_plan()

    generation_run = portia.run_plan(
        image_generation_plan,
        plan_run_inputs={"user_prompt": user_prompt},
        structured_output_schema=OutputSpecialId,
    )

    # Handle clarifications for image generation (e.g., OAuth authentication)
    generation_run = handle_outstanding_clarifications(generation_run, portia)

    # Check if we have a valid result after handling clarifications
    final_output = safe_final_value(generation_run)
    if final_output is None:
        print("Error: Image generation plan did not complete successfully.")
        print("This might be due to authentication issues or plan execution problems.")
        return

    print("Image generation plan result:", final_output)

    # Extract prediction ID and status
    prediction_id, prediction_status = extract_id_and_status(final_output)
    if not prediction_id:
        raise RuntimeError(
            "Could not determine prediction id from create_predictions result"
        )

    print(f"Prediction created: id={prediction_id} status={prediction_status}")

    # Step 3: Poll until images are ready
    print("\n=== Waiting for Images ===")
    final_urls = poll_prediction_until_complete(portia, prediction_id)

    print(f"\nGenerated {len(final_urls)} images:")
    print(json.dumps(final_urls, indent=2))

    if not final_urls:
        print("No image URLs generated. Cannot proceed with social media posting.")
        return

    # Step 4: Let user choose which image to use
    print(f"\n=== Image Selection ===")
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

    print(f"\nSelected image: {chosen_url}")

    # Step 5: Social media posting workflow
    print("\n=== Social Media Posting ===")

    posting_plan_manual = (
        PlanBuilderV2(
            "Post the generated image to social media using the Make.com integration, with platform choice and LLM generated captions"
        )
        .input(
            name="user_preferrence_regarding_posting_prompt",
            description="The user's social media posting preferences - which platform(s) to post to (Instagram, Twitter, or both) and their caption preferences",
        )
        .input(
            name="image_url",
            description="The URL of the selected generated image",
        )
        .input(
            name="original_prompt",
            description="The original prompt used to generate the image",
        )
        .llm_step(
            task="""
            Analyze the user's social media posting preferences and generate appropriate content for each platform.

            Based on the user's input, determine:
            1. Which platform(s) to post to: Instagram, Twitter, or both
            2. Generate an engaging Instagram caption (if posting to Instagram or both)
            3. Generate appropriate Twitter text (if posting to Twitter or both)

            Guidelines:
            - Instagram captions: Engaging, descriptive, can include hashtags unless user specifically says no hashtags, longer format
            - Twitter text: Concise, within character limits, punchy and shareable
            - If posting to both: Create platform-specific content that works for each audience
            - Consider the image content (based on original_prompt) and make captions relevant and engaging
            - Use appropriate tone and style for each platform
            - Respect user's specific requests (like no hashtags, specific greetings, etc.)

            Return the exact platform choice and generated content according to the PostingResult schema.
            """,
            inputs=[
                Input("user_preferrence_regarding_posting_prompt"),
                Input("original_prompt"),
            ],
            output_schema=PostingResult,
            step_name="generate_captions",
        )
        .single_tool_agent_step(
            tool="portia:mcp:custom:us2.make.com:s2795860_mcp_social_post_ig_x_both",
            task="""
            You will call the tool with EXACT JSON arguments.
            Tool expects:
              - channels: string, one of "instagram" | "twitter" | "both"
              - caption: string or null
              - tweet_text: string or null
              - image_url: string (public URL)

            Inputs provided to you:
              - generate_captions: {{ channels, caption, tweet_text }}  // from previous step
              - image_url: string

            Mapping rules:
              - If channels == "instagram": set caption = generate_captions.caption; set tweet_text = null.
              - If channels == "twitter":   set tweet_text = generate_captions.tweet_text; set caption = null.
              - If channels == "both":      set both fields from generate_captions.
              - Always pass through image_url unchanged.

            IMPORTANT: Invoke the tool with exactly these four keys in the JSON body. Do not include extra keys.
            """,
            inputs=[StepOutput("generate_captions"), Input("image_url")],
            step_name="post_to_socials",
        )
        .final_output(output_schema=PostingResult)
        .build()
    )

    posting_run = portia.run_plan(
        posting_plan_manual,
        plan_run_inputs={
            "user_preferrence_regarding_posting_prompt": f"Post on instagram with cute captions with greeting such as good morning or good evening or any other and regarding this image prompt is '{user_prompt}' and dont include hashtags and also post on twitter",
            "image_url": chosen_url,
            "original_prompt": user_prompt,
        },
        structured_output_schema=PostingResult,
    )

    # Handle clarifications (user verification from execution hooks)
    posting_run = handle_outstanding_clarifications(posting_run, portia)

    # Print final result safely
    print("\n=== Final Result ===")
    value = safe_final_value(posting_run)
    if value is None:
        print("Plan finished without a final output (maybe rejected or still pending).")
    else:
        print("Posted successfully!")

        # Show what was actually sent to Make.com (after any user edits)
        from utils.hooks import get_last_posted_payload

        actual_payload = get_last_posted_payload()
        if actual_payload:
            print("Final content that was posted:")
            print(f"  Channels: {actual_payload['channels']}")
            print(f"  Instagram caption: {actual_payload['caption']}")
            print(f"  Twitter text: {actual_payload['tweet_text']}")
            print(f"  Image URL: {actual_payload['image_url']}")
        else:
            print("Original plan output:")
            print(value)

    print("\n=== Run Details ===")
    print(posting_run)


if __name__ == "__main__":
    main()
