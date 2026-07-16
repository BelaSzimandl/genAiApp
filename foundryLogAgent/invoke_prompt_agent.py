from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import json

endpoint = "https://stock-market-ai-resource.services.ai.azure.com/api/projects/stock-market-ai"
client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
openai = client.get_openai_client()

# Invoke via responses API with agent reference
try:
    resp = openai.responses.create(
        model="gpt-5-mini",
        input="Say hello in one short sentence as the log insights assistant.",
        extra_body={"agent": {"name": "log-insights-chatbot", "type": "agent_reference"}},
    )
    print("type", type(resp))
    # extract text
    text = getattr(resp, "output_text", None)
    if text:
        print("OUTPUT:", text)
    else:
        print(resp)
except Exception as e:
    print("invoke error:", type(e), e)
