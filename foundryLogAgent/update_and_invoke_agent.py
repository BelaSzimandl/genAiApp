"""Publish / smoke-test the Foundry prompt agent log-insights-chatbot."""

from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

endpoint = "https://stock-market-ai-resource.services.ai.azure.com/api/projects/stock-market-ai"
client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

sample_csv = Path(r"c:\Users\Bela_Szimandl\Documents\Repos\genAiApp\stockAiApp\data\sample_logs.csv").read_text(
    encoding="utf-8"
)

instructions = f"""You are the AI Log Insights assistant for security and operations monitoring.

You answer natural language questions about structured monitoring logs (CASB, PAM, VulnScanner).
Be concise. Include counts and the most relevant messages.

## Schema
Timestamp, system_name, component, log_level, corr_id, user_ID, message
Levels: DEBUG, INFO, WARN, ERROR, CRITICAL

## Current sample dataset (authoritative for this POC)
```csv
{sample_csv}
```

When answering:
1. Filter/count from the sample dataset above — do not invent rows.
2. For health: ERROR rate = ERROR count / total; DEGRADED if >=30%, WATCH if >=10% or many WARNs, else HEALTHY.
3. For semantic questions (timeouts, threats, suspicious), rank messages by relevance.
4. Present results as a short summary plus a bullet list of matching log lines when useful.

Example queries you handle well:
- Show recent ERROR logs
- Summarize ADMIN activity
- Count logs by level / component
- What's the system health?
- Connection problems / suspicious activity
"""

# Do not attach FunctionTool definitions here: gpt-5-mini shows
# "Not supported by the selected model" in the Foundry playground for those tools,
# and the playground cannot execute client-side functions without a host.

definition = PromptAgentDefinition(
    model="gpt-5-mini",
    instructions=instructions,
    tools=None,
)

agent = client.agents.create_version(
    agent_name="log-insights-chatbot",
    definition=definition,
)
print("updated", agent.name, "v" + str(agent.version), "status", agent.status)

openai = client.get_openai_client()
resp = openai.responses.create(
    model="gpt-5-mini",
    input="Count ERROR logs and list the top 3 ERROR messages.",
    extra_body={"agent_reference": {"name": "log-insights-chatbot", "type": "agent_reference"}},
)
print("OUTPUT:", getattr(resp, "output_text", None) or resp)
