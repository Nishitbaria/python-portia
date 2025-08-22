from portia import (
    PlanBuilderV2,
    StepOutput,
    Input,
)
from utils.config import portia
from utils.schema import PostingResult
from utils.utils_function import handle_outstanding_clarifications, safe_final_value


chosen_url: str = (
    "https://res.cloudinary.com/djqjag779/image/upload/v1755777977/ugc-generator/b9whfesnwhgaomw0o7g0.jpg"
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
        f"user_preferrence_regarding_posting_prompt": f"Post on instagram which cute captions with greeting such as good morning or good evening or any other and regarding this image prompt is {user_prompt} and dont include hashtags and also post on twitter",
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
