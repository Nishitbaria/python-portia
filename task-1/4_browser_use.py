task = """
Find my connections called 'Nishit' on LinkedIn (https://www.linkedin.com)
"""

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
from portia.open_source_tools.browser_tool import (
    BrowserTool,
    BrowserInfrastructureOption,
)


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


browser_tool = BrowserTool(infrastructure_option=BrowserInfrastructureOption.LOCAL)

portia = Portia(
    config=google_config,
    tools=[BrowserTool()],
    execution_hooks=CLIExecutionHooks(),
)

print(portia.run(task).outputs.final_output)
