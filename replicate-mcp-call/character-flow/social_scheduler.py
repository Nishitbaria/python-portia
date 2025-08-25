from portia import PlanBuilderV2
from portia.builder.reference import StepOutput, Input
from pydantic import BaseModel, Field
from utils.config import get_portia_with_custom_tools
import json
from datetime import datetime
from typing import Optional, Dict, Any


# Pydantic models for the social media scheduler
class ChannelDetection(BaseModel):
    """Model for detecting social media channels from user prompt"""

    channel: str  # "both", "instagram", "twitter"
    reasoning: str  # Why this channel was chosen


class CaptionGeneration(BaseModel):
    """Model for generated captions based on channel"""

    instagram_caption: str
    twitter_post: Optional[str] = None  # Only if channel is "both" or "twitter"
    channel: str


class SchedulingData(BaseModel):
    """Final model for Google Sheets integration"""

    media_url: str
    instagram_caption: str
    date_time: str  # ISO format in IST
    twitter_post: Optional[str] = None
    channel: str


class TimeExtraction(BaseModel):
    """Model for extracted time from user prompt"""

    extracted_time: str  # Natural language time like "now", "tomorrow 3pm", etc.
    reasoning: Optional[str] = None  # Why this time was extracted

# System prompts
CHANNEL_DETECTION_PROMPT = """
You are a social media platform detector. Analyze the user's prompt to determine where they want to post.

RULES:
1. Look for keywords like "instagram", "twitter", "both", "all platforms"
2. If no specific platform is mentioned, default to "both"
3. Return the channel as exactly one of: "both", "instagram", "twitter"
4. Provide brief reasoning for your choice

Examples:
- "Post this to Instagram" → channel: "instagram"
- "Share on Twitter only" → channel: "twitter"  
- "Post everywhere" or "both platforms" → channel: "both"
- "Schedule this video" (no platform mentioned) → channel: "both" (default)
"""

CAPTION_GENERATION_PROMPT = """
You are a social media content creator. Generate short, engaging captions based on the video content.

CONTEXT:
- You have a UGC video with product description and dialog
- The video shows someone talking about a product
- Create authentic, relatable content that matches the video's tone

REQUIREMENTS:
- Instagram caption: 1-2 sentences, engaging, can include 1-2 relevant hashtags
- Twitter post: 1 sentence, punchy, under 280 characters (only if channel requires it)
- Keep it simple, authentic, and product-focused
- Match the tone of the original dialog

OUTPUT FORMAT:
- Always provide instagram_caption
- Only provide twitter_post if channel is "both" or "twitter"
"""


def convert_natural_time_to_iso(natural_time_input: str) -> str:
    """Convert natural language time to UTC ISO format (from IST)"""
    from datetime import datetime, timedelta, timezone
    import re

    # IST timezone is UTC+5:30
    IST = timezone(timedelta(hours=5, minutes=30))

    # Get current time in IST
    now_ist = datetime.now(IST)

    # Simple patterns
    if "now" in natural_time_input.lower():
        # Convert IST to UTC
        utc_time = now_ist.astimezone(timezone.utc)
        return utc_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    elif "tomorrow" in natural_time_input.lower():
        tomorrow_ist = now_ist + timedelta(days=1)
        # Extract time if mentioned (e.g., "tomorrow 3pm")
        time_match = re.search(
            r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", natural_time_input.lower()
        )
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            ampm = time_match.group(3)
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            tomorrow_ist = tomorrow_ist.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        # Convert IST to UTC
        utc_time = tomorrow_ist.astimezone(timezone.utc)
        return utc_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    elif "in" in natural_time_input.lower():
        # Handle "in X hours/minutes" format
        hours_match = re.search(r"in\s+(\d+)\s+hours?", natural_time_input.lower())
        minutes_match = re.search(r"in\s+(\d+)\s+minutes?", natural_time_input.lower())

        future_ist = now_ist
        if hours_match:
            hours = int(hours_match.group(1))
            future_ist += timedelta(hours=hours)
        elif minutes_match:
            minutes = int(minutes_match.group(1))
            future_ist += timedelta(minutes=minutes)

        # Convert IST to UTC
        utc_time = future_ist.astimezone(timezone.utc)
        return utc_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    else:
        # Default to 1 hour from now
        future_ist = now_ist + timedelta(hours=1)
        # Convert IST to UTC
        utc_time = future_ist.astimezone(timezone.utc)
        return utc_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")


# Build the simplified social media scheduler plan (no clarifications)
social_scheduler_plan = (
    PlanBuilderV2("Social Media Content Scheduler")
    .input(
        name="user_prompt",
        description="User's scheduling prompt (e.g., 'Post this video to Instagram tomorrow at 3pm')",
    )
    .input(name="media_url", description="Generated video URL from UGC creation")
    .input(
        name="product_description",
        description="Product description from UGC generation",
    )
    .input(name="dialog", description="Dialog text from UGC generation")
    .llm_step(
        task="""
        You are a social media platform detector. Analyze the user's prompt to determine where they want to post.
        
        RULES:
        1. Look for keywords like "instagram", "twitter", "both", "all platforms"
        2. If no specific platform is mentioned, default to "both"
        3. Return the channel as exactly one of: "both", "instagram", "twitter"
        4. Provide brief reasoning for your choice
        
        Analyze this user prompt and determine which social media platforms they want to post to:
        User prompt: [use the user_prompt input]
        
        Return your analysis in the specified format.
        """,
        inputs=[Input("user_prompt")],
        output_schema=ChannelDetection,
        step_name="detect_channels",
    )
    .single_tool_agent_step(
        tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
        task=f"""
        Call the Replicate GPT-4o tool with this EXACT structure:
        {{
          "version": "openai/gpt-4o",
          "input": {{
            "prompt": "Generate social media captions based on this video content:
            Product Description: [use the product_description input]
            Video Dialog: [use the dialog input]
            Target Channel: [use the detect_channels.channel output]
            Create appropriate captions for the specified channel(s). The video shows someone talking about the product described above.",
            "system_prompt": "{CAPTION_GENERATION_PROMPT}"
          }},
          "jq_filter": ".output",
          "Prefer": "wait"
        }}
        
        DO NOT OMIT THE "version" FIELD. It is required and must be "openai/gpt-4o".
        
        IMPORTANT: Extract the caption text from the array output and return it in this format:
        {{
          "instagram_caption": [generated Instagram caption],
          "twitter_post": [generated Twitter post if applicable, otherwise null],
          "channel": [use the detect_channels.channel output]
        }}
        """,
        inputs=[
            Input("product_description"),
            Input("dialog"),
            StepOutput("detect_channels"),
        ],
        output_schema=CaptionGeneration,
        step_name="generate_captions",
    )
    .llm_step(
        task="""
        Extract the scheduling time from the user's prompt. Look for time indicators like:
        - "now" or "immediately" 
        - "tomorrow" with optional time
        - "in X hours/minutes"
        - Specific times like "3pm" or "15:30"
        
        User prompt: [use the user_prompt input]
        
        Return the extracted time in natural language format (e.g., "now", "tomorrow 3pm", "in 2 hours").
        If no time is specified, default to "in 1 hour".
        
        Provide a brief reasoning for why this time was chosen.
        """,
        inputs=[Input("user_prompt")],
        output_schema=TimeExtraction,
        step_name="extract_time",
    )
    .final_output()
    .build()
)


def create_simple_social_scheduler_plan():
    """Create a simplified social scheduler plan that handles everything in one go"""
    return (
        PlanBuilderV2("Simple Social Media Scheduler")
        .input(name="user_prompt", description="User's scheduling prompt")
        .input(name="media_url", description="Video URL")
        .input(name="product_description", description="Product description")
        .input(name="dialog", description="Dialog text")
        .llm_step(
            task="""
            You are a social media platform detector. Analyze the user's prompt to determine where they want to post.
            
            RULES:
            1. Look for keywords like "instagram", "twitter", "both", "all platforms"
            2. If no specific platform is mentioned, default to "both"
            3. Return the channel as exactly one of: "both", "instagram", "twitter"
            4. Provide brief reasoning for your choice
            
            Analyze this user prompt and determine which social media platforms they want to post to:
            User prompt: [use the user_prompt input]
            
            Return your analysis in the specified format.
            """,
            inputs=[Input("user_prompt")],
            output_schema=ChannelDetection,
            step_name="detect_channels",
        )
        .single_tool_agent_step(
            tool="portia:mcp:custom:mcp.replicate.com:create_predictions",
            task="""
            Call the Replicate GPT-4o tool with this EXACT structure:
            {
              "version": "openai/gpt-4o",
              "input": {
                "prompt": "Generate social media captions based on this video content:
                Product Description: [use the product_description input]
                Video Dialog: [use the dialog input]
                Target Channel: [use the detect_channels.channel output]
                Create appropriate captions for the specified channel(s). The video shows someone talking about the product described above.",
                "system_prompt": "You are a social media content creator. Generate short, engaging captions based on the video content. Requirements: Instagram caption: 1-2 sentences, engaging, can include 1-2 relevant hashtags. Twitter post: 1 sentence, punchy, under 280 characters (only if channel requires it). Keep it simple, authentic, and product-focused."
              },
              "jq_filter": ".output",
              "Prefer": "wait"
            }
            
            DO NOT OMIT THE "version" FIELD. It is required and must be "openai/gpt-4o".
            
            IMPORTANT: Extract the caption text from the array output and return it in this format:
            {
              "instagram_caption": [generated Instagram caption],
              "twitter_post": [generated Twitter post if applicable, otherwise null],
              "channel": [use the detect_channels.channel output]
            }
            """,
            inputs=[
                Input("product_description"),
                Input("dialog"),
                StepOutput("detect_channels"),
            ],
            output_schema=CaptionGeneration,
            step_name="generate_captions",
        )
        .llm_step(
            task="""
            Extract the scheduling time from the user's prompt. Look for time indicators like:
            - "now" or "immediately" 
            - "tomorrow" with optional time
            - "in X hours/minutes"
            - Specific times like "3pm" or "15:30"
            
            User prompt: [use the user_prompt input]
            
            Return the extracted time in natural language format (e.g., "now", "tomorrow 3pm", "in 2 hours").
            If no time is specified, default to "in 1 hour".
            
            Provide a brief reasoning for why this time was chosen.
            """,
            inputs=[Input("user_prompt")],
            output_schema=TimeExtraction,
            step_name="extract_time",
        )
        .final_output()
        .build()
    )


def create_sheets_integration_plan(final_data: SchedulingData):
    """Create a plan that saves data to Google Sheets"""
    sheets_plan = (
        PlanBuilderV2("Save social media data to Google Sheets")
        .input(name="media_url", description="Video URL")
        .input(name="instagram_caption", description="Instagram caption")
        .input(name="date_time", description="ISO formatted datetime")
        .input(name="twitter_post", description="Twitter post text")
        .input(name="channel", description="Target channel")
        .single_tool_agent_step(
            tool="portia:mcp:custom:us2.make.com:s2825571_on_demand_add_row_to_sheet",
            task=f"""
            CRITICAL: You MUST use the Make.com tool to add a row to the Google Sheet.
            
            Call the tool "portia:mcp:custom:us2.make.com:s2825571_on_demand_add_row_to_sheet" with this exact payload:
            
            {{
                "media_url": [use the media_url input],
                "instagram_caption": [use the instagram_caption input],
                "date_time": [use the date_time input],
                "twitter_post": [use the twitter_post input],
                "channel": [use the channel input]
            }}
            
            DO NOT call any Google authentication services directly.
            DO NOT use any Google Sheets API directly.
            ONLY use the specified Make.com tool.
            """,
            inputs=[
                Input("media_url"),
                Input("instagram_caption"),
                Input("date_time"),
                Input("twitter_post"),
                Input("channel"),
            ],
            step_name="save_to_sheets",
        )
        .final_output()
        .build()
    )

    return sheets_plan


def main():
    """Main function for simplified social media scheduler (no clarifications)"""
    # Get Portia instance with custom tools
    portia = get_portia_with_custom_tools()

    print("📱 Welcome to Social Media Scheduler!")

    # Get user input
    user_prompt = input(
        "\nDescribe how you want to schedule this post (e.g., 'Post this to Instagram tomorrow at 3pm'): "
    ).strip()

    # These would come from the UGC generation process
    # For now, we'll use example data or get from user
    media_url = input("Video URL from UGC generation: ").strip()
    product_description = input("Product description from UGC: ").strip()
    dialog = input("Dialog from UGC video: ").strip()

    # Run the simplified social scheduler plan
    print("\n🎨 Processing social media scheduling...")
    
    scheduler_plan = create_simple_social_scheduler_plan()
    scheduler_run = portia.run_plan(
        scheduler_plan,
        plan_run_inputs={
            "user_prompt": user_prompt,
            "media_url": media_url,
            "product_description": product_description,
            "dialog": dialog,
        },
    )

    # Extract results from different steps
    step_outputs = scheduler_run.outputs.step_outputs
    
    # Get channel detection result
    channel_result = step_outputs["detect_channels"].value
    print(f"📺 Target channel: {channel_result.channel}")
    
    # Get generated captions
    captions_result = step_outputs["generate_captions"].value
    print(f"📱 Instagram Caption: {captions_result.instagram_caption}")
    if captions_result.twitter_post:
        print(f"🐦 Twitter Post: {captions_result.twitter_post}")
    
    # Get extracted time
    time_result = step_outputs["extract_time"].value
    print(f"⏰ Extracted time: {time_result.extracted_time}")
    if time_result.reasoning:
        print(f"   Reasoning: {time_result.reasoning}")
    
    # Convert natural language time to ISO format
    scheduled_time = convert_natural_time_to_iso(time_result.extracted_time)
    print(f"📅 Scheduled for: {scheduled_time}")

    # Prepare final data for Google Sheets
    final_data = SchedulingData(
        media_url=media_url,
        instagram_caption=captions_result.instagram_caption,
        date_time=scheduled_time,
        twitter_post=captions_result.twitter_post or "",
        channel=captions_result.channel,
    )

    # Save to Google Sheets
    print("\n💾 Saving to Google Sheets...")
    sheets_plan = create_sheets_integration_plan(final_data)
    sheets_run = portia.run_plan(
        sheets_plan,
        plan_run_inputs={
            "media_url": final_data.media_url,
            "instagram_caption": final_data.instagram_caption,
            "date_time": final_data.date_time,
            "twitter_post": final_data.twitter_post,
            "channel": final_data.channel,
        },
    )

    print("\n🎉 Social media post has been scheduled!")
    print(f"✅ Platform(s): {final_data.channel}")
    print(f"📱 Instagram Caption: {final_data.instagram_caption}")
    if final_data.twitter_post:
        print(f"🐦 Twitter Post: {final_data.twitter_post}")
    print(f"⏰ Scheduled Time: {final_data.date_time}")
    print(f"🎥 Video URL: {final_data.media_url}")

    return final_data


if __name__ == "__main__":
    result = main()
