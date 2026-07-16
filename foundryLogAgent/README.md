# Log Insights LLM Chatbot — Azure AI Foundry

Hosted in your Foundry project **stock-market-ai** (West Europe).

## Project links

| Item | Value |
|------|--------|
| Portal home | [stock-market-ai project](https://ai.azure.com/nextgen/r/MKhV0iKbTtKMbbyx_CoFBg,stock-market-ai-rg,,stock-market-ai-resource,stock-market-ai/home) |
| Agent | **log-insights-chatbot** (prompt agent, v2) |
| Model | **gpt-5-mini** (GlobalStandard, capacity 1) |
| Resource group | `stock-market-ai-rg` |
| Account | `stock-market-ai-resource` (**westeurope**) |
| Project endpoint | `https://stock-market-ai-resource.services.ai.azure.com/api/projects/stock-market-ai` |

Open the agent in the portal under **Agents → log-insights-chatbot** and use the playground chat.

## What was added

1. **Model deployment** `gpt-5-mini` on `stock-market-ai-resource`
2. **Prompt agent** `log-insights-chatbot` with:
   - Log-analyst instructions
   - Embedded sample log dataset for POC answers (grounds answers without function tools)
3. Smoke-tested via Responses API (`agent_reference`)

**Note:** Custom `FunctionTool` entries were removed. With `gpt-5-mini` the Foundry playground shows
*“Not supported by the selected model”* and cannot execute client-side functions without a tool host.
Live Cosmos tools need either a **hosted agent** (code) in a supported region (e.g. Sweden/Poland Central)
or an **OpenAPI / Azure Function** tool binding.

## Region notes (important)

- Prefer **West Europe** or **Central Europe-adjacent** regions for your resources (per your preference).
- **Foundry Hosted Agents** (custom Python containers / code deploy) are **not supported in West Europe**. Supported Europe examples: **Sweden Central**, **Poland Central**, **France Central**, **Germany West Central**.
- This project uses a **prompt agent** (works in West Europe) + model `gpt-5-mini`.
- The earlier code-based agent under `agent-framework-agent-with-local-tools-responses/` targets hosted agents; redeploy that only into a project in a hosted-agent region.

## Invoke from CLI

```powershell
cd foundryLogAgent
# uses stockAiApp venv + azure-ai-projects
..\stockAiApp\.venv\Scripts\python.exe .\update_and_invoke_agent.py
```

Or ad-hoc:

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    endpoint="https://stock-market-ai-resource.services.ai.azure.com/api/projects/stock-market-ai",
    credential=DefaultAzureCredential(),
)
openai = client.get_openai_client()
resp = openai.responses.create(
    model="gpt-5-mini",
    input="What's the system health based on the sample logs?",
    extra_body={"agent_reference": {"name": "log-insights-chatbot", "type": "agent_reference"}},
)
print(resp.output_text)
```

## Live Cosmos tools (optional next step)

To run custom Python tools against Cosmos **inside** Foundry as a hosted container agent, create a second project in **Sweden Central** or **Poland Central**, then deploy `agent-framework-agent-with-local-tools-responses` there. The prompt agent in West Europe remains ideal for playground chat with the sample dataset.
