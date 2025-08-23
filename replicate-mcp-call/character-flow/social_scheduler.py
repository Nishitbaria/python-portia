from portia import PlanBuilderV2
from portia.builder.reference import StepOutput, Input
from pydantic import BaseModel
from utils.config import portia
import json
from datetime import datetime
from typing import Optional, Dict, Any
from portia import MultipleChoiceClarification, InputClarification


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
    """Convert natural language time to ISO format in IST timezone"""
    # This is a simplified converter - in production, you'd use a library like dateparser
    from datetime import datetime, timedelta
    import re
    
    now = datetime.now()
    
    # Simple patterns
    if "now" in natural_time_input.lower():
        return now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    elif "tomorrow" in natural_time_input.lower():
        tomorrow = now + timedelta(days=1)
        # Extract time if mentioned (e.g., "tomorrow 3pm")
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', natural_time_input.lower())
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            ampm = time_match.group(3)
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            tomorrow = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return tomorrow.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    else:
        # Default to 1 hour from now
        future = now + timedelta(hours=1)
        return future.strftime("%Y-%m-%dT%H:%M:%S.000Z")


# Build the social media scheduler plan
social_scheduler_plan = (
    PlanBuilderV2("Social Media Content Scheduler")
    .input(
        name="user_prompt", 
        description="User's scheduling prompt (e.g., 'Post this video to Instagram tomorrow at 3pm')"
    )
    .input(
        name="media_url", 
        description="Generated video URL from UGC creation"
    )
    .input(
        name="product_description", 
        description="Product description from UGC generation"
    )
    .input(
        name="dialog", 
        description="Dialog text from UGC generation"
    )
    .llm_step(
        task=f"""
        {CHANNEL_DETECTION_PROMPT}
        
        Analyze this user prompt and determine which social media platforms they want to post to:
        User prompt: [use the user_prompt input]
        
        Return your analysis in the specified format.
        """,
        inputs=[Input("user_prompt")],
        output_schema=ChannelDetection,
        step_name="detect_channels",
    )
    .llm_step(
        task=f"""
        {CAPTION_GENERATION_PROMPT}
        
        Generate social media captions based on this video content:
        
        Product Description: [use the product_description input]
        Video Dialog: [use the dialog input] 
        Target Channel: [use the detect_channels.channel output]
        
        Create appropriate captions for the specified channel(s). The video shows someone talking about the product described above.
        """,
        inputs=[
            Input("product_description"),
            Input("dialog"), 
            StepOutput("detect_channels"),
        ],
        output_schema=CaptionGeneration,
        step_name="generate_captions",
    )
    .final_output(output_schema=CaptionGeneration)
    .build()
)


def create_content_validation_plan(generated_captions: CaptionGeneration):
    """Create a plan that asks user to validate the generated content"""
    content_display = f"""
🎨 Generated Content:
📱 Instagram Caption: {generated_captions.instagram_caption}
"""
    
    if generated_captions.twitter_post:
        content_display += f"🐦 Twitter Post: {generated_captions.twitter_post}\n"
    
    content_display += f"📺 Target Channel(s): {generated_captions.channel}"
    
    validation_plan = portia.plan(f"""
    {content_display}
    
    Please review the generated social media content above. 
    Ask the user if they approve this content or want to make changes.
    If they want changes, ask what specific changes they'd like to make.
    """)
    
    return validation_plan


def create_time_scheduling_plan():
    """Create a plan that asks user for scheduling time"""
    scheduling_plan = portia.plan("""
    Ask the user when they would like to schedule this social media post.
    
    Examples of time formats they can use:
    - "now" - post immediately
    - "tomorrow 3pm" - tomorrow at 3 PM
    - "tomorrow at 15:30" - tomorrow at 3:30 PM
    - "in 2 hours" - 2 hours from now
    
    Ask them to provide the scheduling time in natural language.
    
    IMPORTANT: Do NOT call any Google tools or authentication services. 
    You are only asking for user input, not accessing any external services yet.
    Simply ask the user for their preferred scheduling time and return their response.
    """)
    
    return scheduling_plan


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
                Input("channel")
            ],
            step_name="save_to_sheets",
        )
        .final_output()
        .build()
    )
    
    return sheets_plan


def main():
    """Main function for social media scheduler with UGC data"""
    print("📱 Welcome to Social Media Scheduler!")
    
    # Get user input
    user_prompt = input("\nDescribe how you want to schedule this post (e.g., 'Post this to Instagram tomorrow at 3pm'): ").strip()
    
    # These would come from the UGC generation process
    # For now, we'll use example data or get from user
    media_url = input("Video URL from UGC generation: ").strip()
    product_description = input("Product description from UGC: ").strip()
    dialog = input("Dialog from UGC video: ").strip()
    
    # Step 1: Run initial caption generation plan
    print("\n🎨 Generating captions...")
    caption_run = portia.run_plan(
        social_scheduler_plan,
        plan_run_inputs={
            "user_prompt": user_prompt,
            "media_url": media_url,
            "product_description": product_description,
            "dialog": dialog,
        }
    )
    
    generated_captions = caption_run.outputs.final_output.value
    print(f"Generated captions: {generated_captions}")
    
    # Step 2: Content validation with clarifications
    print("\n✅ Validating content...")
    validation_plan = create_content_validation_plan(generated_captions)
    validation_run = portia.run_plan(validation_plan)
    
    # Handle clarifications for content validation
    final_captions = generated_captions
    while validation_run.state == "NEED_CLARIFICATION":
        clarifications = validation_run.get_outstanding_clarifications()
        for clarification in clarifications:
            if isinstance(clarification, MultipleChoiceClarification):
                print(f"\n{clarification.user_guidance}")
                print("Options:")
                for i, option in enumerate(clarification.options, 1):
                    print(f"{i}. {option}")
                choice = input("Enter your choice (1, 2, 3, etc.): ").strip()
                try:
                    selected_option = clarification.options[int(choice) - 1]
                    validation_run = portia.resolve_clarification(
                        clarification, selected_option, validation_run
                    )
                except (ValueError, IndexError):
                    print("Invalid choice. Please try again.")
            elif isinstance(clarification, InputClarification):
                print(f"\n{clarification.user_guidance}")
                user_input = input("Enter your response: ").strip()
                validation_run = portia.resolve_clarification(
                    clarification, user_input, validation_run
                )
        
        validation_run = portia.resume(validation_run)
    
    # Extract validation result
    validation_result = validation_run.outputs.final_output.value
    print(f"Content validation result: {validation_result}")
    
    # Update captions if user provided changes
    # This is a simplified approach - in real implementation, you'd parse the validation result
    # and potentially re-run caption generation with modifications
    
    # Step 3: Time scheduling with clarifications
    print("\n⏰ Setting schedule time...")
    time_plan = create_time_scheduling_plan()
    time_run = portia.run_plan(time_plan)
    
    # Handle clarifications for time scheduling
    while time_run.state == "NEED_CLARIFICATION":
        clarifications = time_run.get_outstanding_clarifications()
        for clarification in clarifications:
            if isinstance(clarification, MultipleChoiceClarification):
                print(f"\n{clarification.user_guidance}")
                print("Options:")
                for i, option in enumerate(clarification.options, 1):
                    print(f"{i}. {option}")
                choice = input("Enter your choice (1, 2, 3, etc.): ").strip()
                try:
                    selected_option = clarification.options[int(choice) - 1]
                    time_run = portia.resolve_clarification(
                        clarification, selected_option, time_run
                    )
                except (ValueError, IndexError):
                    print("Invalid choice. Please try again.")
            elif isinstance(clarification, InputClarification):
                print(f"\n{clarification.user_guidance}")
                user_input = input("Enter your response: ").strip()
                time_run = portia.resolve_clarification(
                    clarification, user_input, time_run
                )
        
        time_run = portia.resume(time_run)
    
    # Extract time result and convert to ISO format
    time_result = time_run.outputs.final_output.value
    print(f"Time scheduling result: {time_result}")
    
    # Convert natural language time to ISO format
    scheduled_time = convert_natural_time_to_iso(time_result)
    print(f"📅 Scheduled for: {scheduled_time}")
    
    # Step 4: Save to Google Sheets
    print("\n💾 Saving to Google Sheets...")
    
    # Prepare final data
    final_data = SchedulingData(
        media_url=media_url,
        instagram_caption=final_captions.instagram_caption,
        date_time=scheduled_time,
        twitter_post=final_captions.twitter_post or "",
        channel=final_captions.channel
    )
    
    sheets_plan = create_sheets_integration_plan(final_data)
    sheets_run = portia.run_plan(
        sheets_plan,
        plan_run_inputs={
            "media_url": final_data.media_url,
            "instagram_caption": final_data.instagram_caption,
            "date_time": final_data.date_time,
            "twitter_post": final_data.twitter_post,
            "channel": final_data.channel
        }
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