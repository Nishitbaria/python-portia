task = "Read the portialabs.ai website and tell me what they do"


import os
from dotenv import load_dotenv
from portia import (
    Config,
    LLMProvider,
    Portia,
    PortiaToolRegistry,
    StorageClass,
    LogLevel,
)
from portia.cli import CLIExecutionHooks
from portia import McpToolRegistry

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
end_user = "Vinayak_Vispute"

google_config = Config.from_default(
    llm_provider=LLMProvider.GOOGLE,
    default_model="google/gemini-2.0-flash",
    google_api_key=GOOGLE_API_KEY,
    storage_class=StorageClass.CLOUD,
    default_log_level=LogLevel.DEBUG,
)

registry = McpToolRegistry.from_stdio_connection(
    server_name="fetch",
    command="uvx",
    args=["mcp-server-fetch"],
)

portia = Portia(
    config=google_config,
    tools=PortiaToolRegistry(google_config) + registry,
)

print(portia.run(task).outputs.final_output)
