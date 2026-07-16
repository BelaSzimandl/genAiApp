from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

endpoint = "https://stock-market-ai-resource.services.ai.azure.com/api/projects/stock-market-ai"
client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

instructions = """You are the AI Log Insights assistant for security and operations monitoring.

You help analysts query and reason about structured monitoring logs (CASB, PAM, VulnScanner, etc.).
Always be concise and operational. Prefer summaries with counts and key messages.

Log schema fields:
- Timestamp, system_name, component, log_level, corr_id, user_ID, message
Common components: CASB, PAM, VulnScanner
Levels: DEBUG, INFO, WARN, ERROR, CRITICAL

When tools are available (filter/count/health/semantic search), use them instead of guessing.
When tools are not available, ask the user for log excerpts or explain how to attach the Cosmos-backed tools.

Example questions:
- Show recent ERROR logs
- Summarize ADMIN activity  
- Count logs by level / component
- What's the system health?
- Connection problems / suspicious activity
"""

definition = PromptAgentDefinition(
    model="gpt-5-mini",
    instructions=instructions,
)

agent = client.agents.create_version(
    agent_name="log-insights-chatbot",
    definition=definition,
)
print("created:", getattr(agent, "name", None), getattr(agent, "version", None), getattr(agent, "id", None))
print(agent)
