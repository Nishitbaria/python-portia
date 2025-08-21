# A more complex task:
task1 = """
Check my availability in Google Calendar for 18 August 2025 between 2pm and 3pm.
If I have at least 60 minutes of continuous free time between 2pm and 3pm, schedule the meeting. If not, give me the next free slot after 4pm. with Dean Ambrose (vinayakvispute262003@gmail.com) with title 'Encode Hackathon', and description 'hack it'.
schedule the meeting. If not, give me the next free slot after 4pm. please output the next time after 4pm when I am free.
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
from portia import open_source_tool_registry


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

portia = Portia(
    config=google_config,
    tools=PortiaToolRegistry(google_config) + open_source_tool_registry,
    execution_hooks=CLIExecutionHooks(),
)

plan = portia.plan(task1)
print(plan.pretty_print())

plan_run = portia.run_plan(plan, end_user=end_user)
