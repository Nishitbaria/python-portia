# my_tools/image_picker_tool.py
from typing import Any
import json
import re
from pydantic import BaseModel, Field
from portia import (
    Tool,
    ToolRunContext,
    MultipleChoiceClarification,
    ClarificationCategory,
)


class ImagePickerArgs(BaseModel):
    urls: Any = Field(
        ..., description="List of image URLs to pick from or a string containing them"
    )


class ImagePickerTool(Tool[str]):
    id: str = "image_picker_tool"
    name: str = "Image Picker"
    description: str = "Ask user to pick one image URL from a list"
    args_schema: type[BaseModel] = ImagePickerArgs
    output_schema: tuple[str, str] = ("str", "The chosen image URL")

    def run(self, ctx: ToolRunContext, urls: Any) -> str | MultipleChoiceClarification:
        # If a previous clarification for this step was resolved, return it directly
        try:
            # Prefer step-scoped clarification if available
            step_clar = ctx.plan_run.get_clarification_for_step(
                ClarificationCategory.MULTIPLE_CHOICE
            )
            if (
                step_clar
                and getattr(step_clar, "resolved", False)
                and getattr(step_clar, "response", None)
            ):
                resp = step_clar.response
                if isinstance(resp, str) and resp.startswith("http"):
                    return resp

            # Fallback: search all clarifications on the run
            for c in ctx.plan_run.outputs.clarifications:
                if (
                    getattr(c, "category", None)
                    == ClarificationCategory.MULTIPLE_CHOICE
                    and getattr(c, "argument_name", None) == "urls"
                    and getattr(c, "resolved", False)
                    and getattr(c, "response", None)
                ):
                    response_val = c.response
                    if isinstance(response_val, str) and response_val.startswith(
                        "http"
                    ):
                        return response_val
        except Exception:
            pass

        # Normalize various representations into a list[str] of URLs
        def extract_urls(value: Any) -> list[str]:
            pattern = r"https://[^\s\"\]]+\.(?:png|jpg|jpeg|webp)"

            # Already a list of URLs
            if isinstance(value, list):
                if all(isinstance(x, str) and x.startswith("http") for x in value):
                    return value
                return re.findall(pattern, "\n".join(str(x) for x in value))

            # Dict shape with content/text
            if isinstance(value, dict):
                if (
                    "content" in value
                    and isinstance(value["content"], list)
                    and value["content"]
                ):
                    first = value["content"][0]
                    if isinstance(first, dict) and "text" in first:
                        try:
                            parsed = json.loads(
                                first["text"]
                            )  # may be JSON array string
                            return extract_urls(parsed)
                        except json.JSONDecodeError:
                            return re.findall(pattern, first["text"])
                return re.findall(pattern, json.dumps(value))

            # String: try JSON first, else regex
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    return extract_urls(parsed)
                except json.JSONDecodeError:
                    return re.findall(pattern, value)

            return re.findall(pattern, str(value))

        # If the user has already provided a single URL, return it directly to avoid re-asking
        if isinstance(urls, str) and urls.startswith("http"):
            return urls
        if (
            isinstance(urls, list)
            and all(isinstance(x, str) for x in urls)
            and len(urls) == 1
            and urls[0].startswith("http")
        ):
            return urls[0]

        url_list = extract_urls(urls)
        if len(url_list) == 1:
            return url_list[0]

        return MultipleChoiceClarification(
            plan_run_id=ctx.plan_run.id,
            argument_name="urls",
            user_guidance="Multiple images generated. Choose one URL to continue.",
            options=url_list,
        )
