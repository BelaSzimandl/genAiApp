from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import inspect

endpoint = "https://stock-market-ai-resource.services.ai.azure.com/api/projects/stock-market-ai"
client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
print("agents attrs:", [a for a in dir(client.agents) if not a.startswith("_")])
# try create patterns
try:
    from azure.ai.projects.models import PromptAgentDefinition
    print("PromptAgentDefinition fields", getattr(PromptAgentDefinition, "__annotations__", None) or PromptAgentDefinition.__doc__)
except Exception as e:
    print("PromptAgentDefinition import", e)

try:
    from azure.ai.agents.models import PromptAgentDefinition as P2
    print("agents.models PromptAgentDefinition ok")
except Exception as e:
    print("agents.models", e)
