# A relatively simple task:
task0 = "Star the github repo for portiaAI/portia-sdk-python"


import os
from dotenv import load_dotenv
from portia import (
    Config,
    LLMProvider,
    Portia,
    PortiaToolRegistry,
    StorageClass,
    LogLevel,
    DefaultToolRegistry
)
from portia.cli import CLIExecutionHooks


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

google_config = Config.from_default(
    llm_provider=LLMProvider.OPENAI,
    default_model="openai/gpt-4o",
    openai_api_key=OPENAI_API_KEY,
    storage_class=StorageClass.DISK,
    default_log_level=LogLevel.DEBUG,
)

portia = Portia(
    config=google_config,
    tools=PortiaToolRegistry(google_config),
    execution_hooks=CLIExecutionHooks(),
)
    
plan_run = portia.run(task0, end_user="end_user-01")
