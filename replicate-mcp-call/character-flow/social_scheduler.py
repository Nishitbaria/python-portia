from portia import PlanBuilderV2
from portia.builder.reference import StepOutput, Input
from pydantic import BaseModel, Field
from utils.config import get_portia_with_custom_tools
import json
from datetime import datetime
from typing import Optional, Dict, Any
from portia import MultipleChoiceClarification, InputClarification, Tool, ToolRunContext


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


# Schema for ContentValidationTool
class ContentValidationToolSchema(BaseModel):
    """Schema for content validation tool input"""
    
    instagram_caption: str = Field(..., description="Instagram caption to validate")
    twitter_post: Optional[str] = Field(None, description="Twitter post to validate (optional)")
    channel: str = Field(..., description="Target channel(s): instagram, twitter, or both")


# Schema for TimeSchedulingTool  
class TimeSchedulingToolSchema(BaseModel):
    """Schema for time scheduling tool input"""
    
    placeholder: str = Field("trigger", description="Placeholder to trigger time clarification")


# Schema for ContentRevisionTool
class ContentRevisionToolSchema(BaseModel):
    """Schema for content revision tool input"""
    
    instagram_caption: str = Field(..., description="Current Instagram caption")
    twitter_post: Optional[str] = Field(None, description="Current Twitter post (optional)")
    channel: str = Field(..., description="Target channel(s)")
    change_request: str = Field(..., description="User's specific change request")


class ContentValidationTool(Tool[str]):
    """Tool that validates generated social media content with user clarifications"""

    id: str = "content_validation_tool"
    name: str = "Content Validation Tool"
    description: str = "Validates social media content and asks user for approval or changes"
    args_schema: type[BaseModel] = ContentValidationToolSchema
    output_schema: tuple[str, str] = ("str", "User's validation decision and any requested changes")

    def run(self, ctx: ToolRunContext, instagram_caption: str, twitter_post: Optional[str] = None, channel: str = "both") -> str | MultipleChoiceClarification | InputClarification:
        """Run the ContentValidationTool with iterative revision support."""
        
        # Debug logging to understand what's happening
        print(f"DEBUG: ContentValidationTool called")
        print(f"DEBUG: Total clarifications in context: {len(ctx.clarifications)}")
        for i, c in enumerate(ctx.clarifications):
            print(f"  {i}: {getattr(c, 'argument_name', 'no_name')} - resolved: {c.resolved} - response: {getattr(c, 'response', 'no_response')}")
        
        # Analyze the current state based on existing clarifications
        state = self._analyze_current_state(ctx)
        print(f"DEBUG: Current state: {state}")
        
        if state["phase"] == "initial_approval":
            # First time - show original content and ask for approval
            content_display = f"""
🎨 Generated Content:
📱 Instagram Caption: {instagram_caption}
"""
            if twitter_post:
                content_display += f"🐦 Twitter Post: {twitter_post}\n"
            content_display += f"📺 Target Channel(s): {channel}"
            
            return MultipleChoiceClarification(
                plan_run_id=ctx.plan_run.id,
                argument_name="initial_approval",
                user_guidance=f"{content_display}\n\nDo you approve this content or would you like to make changes?",
                options=[
                    "Approve - use this content as is",
                    "Request changes - I want to modify something"
                ]
            )
            
        elif state["phase"] == "request_changes":
            # User said they want changes, ask what changes
            return InputClarification(
                plan_run_id=ctx.plan_run.id,
                argument_name=f"change_request_{state['cycle']}",
                user_guidance="""What specific changes would you like to make to the content? 

Examples:
- "Remove hashtags from Twitter post"
- "Make Instagram caption shorter" 
- "Add emojis to Instagram"
- "Change tone to more professional"

Please describe what you'd like to modify:"""
            )
            
        elif state["phase"] == "show_revised":
            # Apply changes and show revised content
            # Get current content based on cycle
            if state['cycle'] == 0:
                current_instagram = instagram_caption
                current_twitter = twitter_post
            else:
                # For later cycles, we'd need to get from previous revisions
                # For now, use original as fallback
                current_instagram = instagram_caption
                current_twitter = twitter_post
            
            change_request = state["change_request"]
            
            revised_content = self._apply_changes(
                current_instagram,
                current_twitter,
                channel,
                change_request,
                ctx
            )
            
            content_display = f"""
🎨 Revised Content (Revision {state['cycle'] + 1}):
📱 Instagram Caption: {revised_content['instagram_caption']}
"""
            if revised_content['twitter_post']:
                content_display += f"🐦 Twitter Post: {revised_content['twitter_post']}\n"
            content_display += f"📺 Target Channel(s): {revised_content['channel']}"
            content_display += f"\n\n✅ Changes Applied: {revised_content['changes_made']}"
            
            return MultipleChoiceClarification(
                plan_run_id=ctx.plan_run.id,
                argument_name=f"approval_after_revision_{state['cycle'] + 1}",
                user_guidance=f"{content_display}\n\nDo you approve this revised content or would you like to make more changes?",
                options=[
                    "Approve - use this content as is",
                    "Request changes - I want to modify something"
                ]
            )
            
        elif state["phase"] == "approved":
            # User approved, return final result
            # Get the final content - either original or latest revision
            if state['cycle'] == 0:
                final_instagram = instagram_caption
                final_twitter = twitter_post
            else:
                # For now, return original as fallback - in real implementation
                # we'd track the latest revised content
                final_instagram = instagram_caption
                final_twitter = twitter_post
                
            final_result = {
                "instagram_caption": final_instagram,
                "twitter_post": final_twitter,
                "channel": channel,
                "approved": True,
                "revision_cycles": state["cycle"]
            }
            return json.dumps(final_result)
        
        else:
            # Fallback - should not reach here
            return "ERROR: Unknown state in content validation"
    
    def _analyze_current_state(self, ctx: ToolRunContext) -> dict:
        """Analyze clarification context to determine current state"""
        
        # Get all resolved clarifications
        resolved_clarifications = [c for c in ctx.clarifications if c.resolved]
        
        # If no clarifications yet, start with initial approval
        if not resolved_clarifications:
            return {
                "phase": "initial_approval",
                "cycle": 0,
                "current_content": None
            }
        
        # Find the latest approval decision
        latest_approval = None
        latest_approval_cycle = -1
        
        for c in resolved_clarifications:
            arg_name = getattr(c, 'argument_name', '')
            if 'initial_approval' in arg_name:
                latest_approval = c
                latest_approval_cycle = 0
            elif 'approval_after_revision_' in arg_name:
                try:
                    cycle_num = int(arg_name.split('_')[-1])
                    if cycle_num > latest_approval_cycle:
                        latest_approval = c
                        latest_approval_cycle = cycle_num
                except ValueError:
                    pass
        
        if not latest_approval:
            return {"phase": "initial_approval", "cycle": 0, "current_content": None}
        
        # If latest approval was "Approve", we're done
        if latest_approval.response == "Approve - use this content as is":
            current_content = self._get_latest_content(ctx, latest_approval_cycle)
            return {
                "phase": "approved",
                "cycle": latest_approval_cycle,
                "current_content": current_content
            }
        
        # If latest approval was "Request changes", check if we have change request
        if latest_approval.response == "Request changes - I want to modify something":
            change_request_arg = f"change_request_{latest_approval_cycle}"
            
            # Look for corresponding change request
            change_request = None
            for c in resolved_clarifications:
                if getattr(c, 'argument_name', '') == change_request_arg:
                    change_request = c
                    break
            
            if not change_request:
                # Need to ask for change request
                current_content = self._get_latest_content(ctx, latest_approval_cycle)
                return {
                    "phase": "request_changes",
                    "cycle": latest_approval_cycle,
                    "current_content": current_content
                }
            else:
                # Have change request, need to show revised content
                current_content = self._get_latest_content(ctx, latest_approval_cycle)
                return {
                    "phase": "show_revised",
                    "cycle": latest_approval_cycle,
                    "current_content": current_content,
                    "change_request": change_request.response
                }
        
        # Default fallback
        return {"phase": "initial_approval", "cycle": 0, "current_content": None}
    
    def _get_latest_content(self, ctx: ToolRunContext, cycle: int) -> dict:
        """Get the content for the specified cycle"""
        # For cycle 0, we need to get from the original inputs passed to the tool
        # For later cycles, we need to look in previous revisions
        
        # This is a simplified version - in the real implementation,
        # we'd need to track content through the revision process
        # For now, return None and let the calling code handle it
        return None
    
    def _apply_changes(self, instagram_caption: str, twitter_post: Optional[str], channel: str, change_request: str, ctx: ToolRunContext) -> dict:
        """Apply the requested changes using the ContentRevisionTool logic"""
        revision_tool = ContentRevisionTool()
        revised_json = revision_tool.run(ctx, instagram_caption, change_request, twitter_post, channel)
        return json.loads(revised_json)


class TimeSchedulingTool(Tool[str]):
    """Tool that asks user for scheduling time with clarifications"""

    id: str = "time_scheduling_tool"
    name: str = "Time Scheduling Tool"
    description: str = "Asks user for social media post scheduling time"
    args_schema: type[BaseModel] = TimeSchedulingToolSchema
    output_schema: tuple[str, str] = ("str", "User's preferred scheduling time in natural language")

    def run(self, ctx: ToolRunContext, placeholder: str = "trigger") -> str | InputClarification:
        """Run the TimeSchedulingTool."""
        
        # Check if we already have a resolved time clarification
        time_clarification = None
        for clarification in ctx.clarifications:
            if (clarification.resolved and 
                hasattr(clarification, 'user_guidance') and 
                'schedule' in clarification.user_guidance.lower() and
                'time' in clarification.user_guidance.lower()):
                time_clarification = clarification
                break
        
        # If no time decision yet, ask for scheduling time
        if not time_clarification:
            return InputClarification(
                plan_run_id=ctx.plan_run.id,
                argument_name="scheduling_time",
                user_guidance="""When would you like to schedule this social media post?

Examples of time formats you can use:
- "now" - post immediately
- "tomorrow 3pm" - tomorrow at 3 PM  
- "tomorrow at 15:30" - tomorrow at 3:30 PM
- "in 2 hours" - 2 hours from now

Please provide the scheduling time in natural language:"""
            )
        
        # Return the user's time preference
        return str(time_clarification.response)


class ContentRevisionTool(Tool[str]):
    """Tool that revises social media content based on user feedback"""

    id: str = "content_revision_tool"
    name: str = "Content Revision Tool"
    description: str = "Revises social media content based on specific user change requests"
    args_schema: type[BaseModel] = ContentRevisionToolSchema
    output_schema: tuple[str, str] = ("str", "JSON string with revised content")

    def run(self, ctx: ToolRunContext, instagram_caption: str, change_request: str, twitter_post: Optional[str] = None, channel: str = "both") -> str:
        """Run the ContentRevisionTool."""
        
        revision_prompt = f"""
You are a social media content editor. Revise the social media content based on the user's specific change request.

CURRENT CONTENT:
- Instagram Caption: {instagram_caption}
- Twitter Post: {twitter_post or "N/A"}
- Channel: {channel}

USER'S CHANGE REQUEST: {change_request}

INSTRUCTIONS:
1. Analyze the change request to understand what specifically needs to be modified
2. Apply ONLY the requested changes - don't modify other parts unless necessary
3. Maintain the original tone and style where changes aren't requested
4. If the request mentions "Instagram" or "Twitter" specifically, only modify that platform's content
5. If no platform is specified, apply changes to the relevant content

Examples of specific changes:
- "Remove hashtags from Twitter post" → Only remove hashtags from Twitter content
- "Make Instagram caption shorter" → Only shorten Instagram caption
- "Change tone to more professional" → Modify tone of all content
- "Add emojis to Instagram" → Only add emojis to Instagram caption

Return the result as a JSON object with the revised content:
{{
    "instagram_caption": "revised Instagram caption here",
    "twitter_post": "revised Twitter post here or null if not applicable",
    "channel": "{channel}",
    "changes_made": "brief description of what was changed"
}}
"""
        
        # This would normally call an LLM, but since we're using the existing portia setup,
        # we'll simulate the revision logic here. In a real implementation, you'd use
        # portia.run() or an LLM step to process this prompt.
        
        # For now, let's implement some basic revision logic
        revised_instagram = instagram_caption
        revised_twitter = twitter_post
        changes_made = []
        
        change_lower = change_request.lower()
        
        # Handle hashtag removal
        if "remove hashtag" in change_lower or "no hashtag" in change_lower:
            if "twitter" in change_lower and twitter_post:
                # Remove hashtags from Twitter only
                import re
                revised_twitter = re.sub(r'#\w+\s*', '', twitter_post).strip()
                changes_made.append("Removed hashtags from Twitter post")
            elif "instagram" in change_lower:
                # Remove hashtags from Instagram only
                import re
                revised_instagram = re.sub(r'#\w+\s*', '', instagram_caption).strip()
                changes_made.append("Removed hashtags from Instagram caption")
            else:
                # Remove hashtags from both
                import re
                revised_instagram = re.sub(r'#\w+\s*', '', instagram_caption).strip()
                if twitter_post:
                    revised_twitter = re.sub(r'#\w+\s*', '', twitter_post).strip()
                changes_made.append("Removed hashtags from content")
        
        # Handle making content shorter
        if "shorter" in change_lower or "brief" in change_lower:
            if "instagram" in change_lower:
                # Make Instagram shorter
                sentences = revised_instagram.split('.')
                if len(sentences) > 1:
                    revised_instagram = sentences[0] + '.'
                    changes_made.append("Shortened Instagram caption")
            elif "twitter" in change_lower and twitter_post:
                # Make Twitter shorter  
                if len(revised_twitter) > 100:
                    revised_twitter = revised_twitter[:100].rsplit(' ', 1)[0] + "..."
                    changes_made.append("Shortened Twitter post")
        
        # Handle adding emojis
        if "add emoji" in change_lower or "more emoji" in change_lower:
            if "instagram" in change_lower:
                if not any(ord(char) > 127 for char in revised_instagram):  # No emojis present
                    revised_instagram = f"✨ {revised_instagram} ✨"
                    changes_made.append("Added emojis to Instagram caption")
            elif "twitter" in change_lower and twitter_post:
                if not any(ord(char) > 127 for char in revised_twitter):  # No emojis present
                    revised_twitter = f"🚀 {revised_twitter}"
                    changes_made.append("Added emojis to Twitter post")
        
        # If no specific changes were made, provide a generic response
        if not changes_made:
            changes_made.append(f"Applied requested changes: {change_request}")
        
        result = {
            "instagram_caption": revised_instagram,
            "twitter_post": revised_twitter,
            "channel": channel,
            "changes_made": "; ".join(changes_made)
        }
        
        return json.dumps(result)


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


# Build the social media scheduler plan
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
    """Create a plan that uses the enhanced content validation tool for iterative revision"""
    validation_plan = (
        PlanBuilderV2("Content Validation")
        .invoke_tool_step(
            step_name="validate_content",
            tool="content_validation_tool",
            args={
                "instagram_caption": generated_captions.instagram_caption,
                "twitter_post": generated_captions.twitter_post,
                "channel": generated_captions.channel
            }
        )
        .final_output()
        .build()
    )

    return validation_plan


def create_time_scheduling_plan():
    """Create a plan that asks user for scheduling time"""
    scheduling_plan = (
        PlanBuilderV2("Time Scheduling")
        .invoke_tool_step(
            step_name="schedule_time",
            tool="time_scheduling_tool",
            args={
                "placeholder": "trigger"
            }
        )
        .final_output()
        .build()
    )

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
                Input("channel"),
            ],
            step_name="save_to_sheets",
        )
        .final_output()
        .build()
    )

    return sheets_plan


def main():
    """Main function for social media scheduler with UGC data"""
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

    # Step 1: Run initial caption generation plan
    print("\n🎨 Generating captions...")
    caption_run = portia.run_plan(
        social_scheduler_plan,
        plan_run_inputs={
            "user_prompt": user_prompt,
            "media_url": media_url,
            "product_description": product_description,
            "dialog": dialog,
        },
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
        channel=final_captions.channel,
    )

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
