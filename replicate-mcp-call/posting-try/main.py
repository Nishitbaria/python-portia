from portia import (
    PlanBuilderV2,
    StepOutput,
    Input,
)
from utils.config import portia
from utils.schema import PostingResult
from utils.utils_function import handle_outstanding_clarifications, safe_final_value


chosen_url: str = (
    "https://replicate.delivery/xezq/4QunPWD6mIoZF1AzPwPGfB5kzr9Pzc0YgpkfK0sWv4fkwoaqA/out-1.webp"
)


user_prompt = (
    "A modern, minimalist, white background with a small white house in the middle"
)


posting_plan_manual = (
    PlanBuilderV2(
        f"Post the image to social media using the Make.com integration, with the choice of instagram, twitter, or both and also with llm generated caption"
    )
    .input(
        name="user_preferrence_regarding_posting_prompt",
        description="The user's social media posting preferences - which platform(s) to post to (Instagram, Twitter, or both) and their caption preferences (use AI-generated caption, provide custom caption, or modify the AI suggestion)",
    )
    .input(
        name="image_url",
        description="The URL of the generated image",
    )
    .llm_step(
        task="""
        Analyze the user's social media posting preferences and generate appropriate content for each platform.

        Based on the user's input, determine:
        1. Which platform(s) to post to: Instagram, Twitter, or both
        2. Generate an engaging Instagram caption (if posting to Instagram or both)
        3. Generate appropriate Twitter text (if posting to Twitter or both)

        Guidelines:
        - Instagram captions: Engaging, descriptive, can include hashtags, longer format
        - Twitter text: Concise, within character limits, punchy and shareable
        - If posting to both: Create platform-specific content that works for each audience
        - Consider the image content and make captions relevant and engaging
        - Use appropriate tone and style for each platform

        Return the exact platform choice and generated content according to the PostingResult schema.
        """,
        inputs=[Input("user_preferrence_regarding_posting_prompt")],
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
          - generate_captions: { channels, caption, tweet_text }  // from previous step
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
        f"user_preferrence_regarding_posting_prompt": f"Post on instagram which cute captions with greeting such as good morning or good evening or any other and regarding this image prompt is {user_prompt} and dont include # tags",
        "image_url": chosen_url,
    },
    structured_output_schema=PostingResult,
)

posting_run = handle_outstanding_clarifications(posting_run, portia)


# Print final result safely
value = safe_final_value(posting_run)
if value is None:
    print("Plan finished without a final output (maybe rejected or still pending).")
else:
    print(value)

print("===")
print(posting_run)
# tweet_text
# caption
# channels

# # Use clarification to get posting preferences
# posting_plan = portia.plan(
#     f"""
#         Ask the user where they want to post the image: Instagram, Twitter, or both.
#         The image URL is: {chosen_url}
#         The original prompt was: {user_prompt}
#         """
# )


# Handle clarifications for posting preferences
#     while posting_run.state == "NEED_CLARIFICATION":
#         clarifications = posting_run.get_outstanding_clarifications()
#         for clarification in clarifications:
#             if isinstance(clarification, MultipleChoiceClarification):
#                 print(f"\n{clarification.user_guidance}")
#                 print("Options:")
#                 for i, option in enumerate(clarification.options, 1):
#                     print(f"{i}. {option}")
#                 choice = input("Enter your choice (1, 2, 3, etc.): ").strip()
#                 try:
#                     selected_option = clarification.options[int(choice) - 1]
#                     posting_run = portia.resolve_clarification(
#                         clarification, selected_option, posting_run
#                     )
#                 except (ValueError, IndexError):
#                     print("Invalid choice. Please try again.")
#             elif isinstance(clarification, InputClarification):
#                 print(f"\n{clarification.user_guidance}")
#                 user_input = input("Enter your response: ").strip()
#                 posting_run = portia.resolve_clarification(
#                     clarification, user_input, posting_run
#                 )

#         posting_run = portia.resume(posting_run)

#     # Extract posting preference from the run
#     posting_preference = posting_run.outputs.final_output.value.lower()

#     # Determine channels based on user preference
#     if "instagram" in posting_preference and "twitter" in posting_preference:
#         channels = "both"
#     elif "instagram" in posting_preference:
#         channels = "instagram"
#     elif "twitter" in posting_preference:
#         channels = "twitter"
#     else:
#         print("Could not determine posting preference. Defaulting to Instagram.")
#         channels = "instagram"

#     print(f"\nPosting to: {channels}")

#     # Generate caption using PlanBuilderV2
#     caption_plan = (
#         PlanBuilderV2(
#             f"Generate engaging social media captions for an image about {user_prompt}"
#         )
#         .input(name="image_url", description="The URL of the generated image")
#         .input(
#             name="original_prompt",
#             description="The original prompt used to generate the image",
#         )
#         .input(
#             name="channels", description="Where to post: instagram, twitter, or both"
#         )
#         .llm_step(
#             task=f"""
#             Generate engaging social media captions for an image.

#             Image URL: {chosen_url}
#             Original prompt: {user_prompt}
#             Posting to: {channels}

#             Create:
#             1. An Instagram caption (engaging, descriptive, with relevant hashtags)
#             2. A Twitter post text (shorter, punchy, within character limits)

#             Make them engaging, relevant to the image content, and appropriate for each platform.
#             Use emojis where appropriate but don't overdo it.
#             """,
#             inputs=[Input("image_url"), Input("original_prompt"), Input("channels")],
#             output_schema=CaptionGenerationResult,
#             step_name="generate_captions",
#         )
#         .final_output(output_schema=CaptionGenerationResult)
#         .build()
#     )

#     caption_run = portia.run_plan(
#         caption_plan,
#         plan_run_inputs={
#             "image_url": chosen_url,
#             "original_prompt": user_prompt,
#             "channels": channels,
#         },
#     )

#     generated_caption = caption_run.outputs.final_output.value.caption
#     generated_tweet = (
#         caption_run.outputs.final_output.value.tweet_text or generated_caption
#     )

#     print(f"\nGenerated Instagram Caption:")
#     print(generated_caption)
#     if channels in ["twitter", "both"]:
#         print(f"\nGenerated Tweet Text:")
#         print(generated_tweet)

#     # Validate caption with user
#     while True:
#         validation_choice = (
#             input("\nDo you want to use this caption? (yes/no/regenerate): ")
#             .strip()
#             .lower()
#         )

#         if validation_choice in ["yes", "y"]:
#             break
#         elif validation_choice in ["no", "n"]:
#             print("Caption rejected. Exiting without posting.")
#             exit(0)
#         elif validation_choice in ["regenerate", "r"]:
#             # Regenerate caption
#             caption_run = portia.run_plan(
#                 caption_plan,
#                 plan_run_inputs={
#                     "image_url": chosen_url,
#                     "original_prompt": user_prompt,
#                     "channels": channels,
#                 },
#             )

#             generated_caption = caption_run.outputs.final_output.value.caption
#             generated_tweet = (
#                 caption_run.outputs.final_output.value.tweet_text or generated_caption
#             )

#             print(f"\nNew Generated Instagram Caption:")
#             print(generated_caption)
#             if channels in ["twitter", "both"]:
#                 print(f"\nNew Generated Tweet Text:")
#                 print(generated_tweet)
#         else:
#             print("Please enter 'yes', 'no', or 'regenerate'")

#     # Post to social media
#     print(f"\nPosting to {channels}...")

#     posting_payload = {
#         "channels": channels,
#         "caption": generated_caption,
#         "tweet_text": generated_tweet if channels in ["twitter", "both"] else "",
#         "image_url": chosen_url,
#     }

#     social_plan = portia.plan(
#         f"""
#         Post the image to social media using the Make.com integration.

#         Payload:
#         {json.dumps(posting_payload, indent=2)}

#         Use the tool 'portia:mcp:custom:us2.make.com:s2795860_mcp_social_post_ig_x_both'
#         with the exact payload above.
#         """
#     )

#     social_run = portia.run_plan(social_plan)
#     print("\nSocial Media Post Result:")
#     print(social_run.outputs.final_output.value)

# else:
#     print("No image URLs generated. Cannot proceed with social media posting.")
