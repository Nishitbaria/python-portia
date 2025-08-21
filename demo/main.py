import os
from dotenv import load_dotenv
from portia import (
    Config,
    LLMProvider,
    Portia,
    example_tool_registry,
    StorageClass,
    LogLevel,
)

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

google_config = Config.from_default(
    llm_provider=LLMProvider.GOOGLE,
    default_model="google/gemini-2.0-flash",
    google_api_key=GOOGLE_API_KEY,
    storage_class=StorageClass.DISK,
    default_log_level=LogLevel.DEBUG,
    planning_model="google/gemini-2.0-flash",
)

portia = Portia(config=google_config, tools=example_tool_registry)

plan_run = portia.run("add 1 + 2")

print(plan_run.model_dump_json(indent=6))
