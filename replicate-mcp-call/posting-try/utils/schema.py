from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class OutputSpecialId(BaseModel):
    id: str
    status: str


class PredictionPollResult(BaseModel):
    status: str
    output: Optional[List[str]] = None


class CaptionGenerationResult(BaseModel):
    caption: str
    tweet_text: Optional[str] = None


class PostingResult(BaseModel):
    caption: Optional[str] = Field(
        ...,
        description="The caption text for Instagram posts. Required when posting to Instagram or both platforms, otherwise None.",
    )
    tweet_text: Optional[str] = Field(
        ...,
        description="The text content for Twitter posts. Required when posting to Twitter or both platforms, otherwise None.",
    )
    channels: Literal["twitter", "instagram", "both"] = Field(
        ...,
        description="The target social media platform(s) for posting: 'twitter' for Twitter only, 'instagram' for Instagram only, or 'both' for both platforms.",
    )
