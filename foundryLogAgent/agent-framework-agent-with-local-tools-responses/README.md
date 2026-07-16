# Log Insights — Azure AI Foundry Hosted Agent (code deploy)

LLM chatbot for security/monitoring logs with tools over **Azure Cosmos DB**.

**Prefer West/Central Europe for resources.** Note: **Foundry Hosted Agents are not supported in West Europe.** Use **Sweden Central**, **Poland Central**, **France Central**, or **Germany West Central** for code-deployed agents.

The agent currently used in project **stock-market-ai** (West Europe) is the **prompt agent** `log-insights-chatbot` — see `../README.md`.

Portal: [Azure AI Foundry](https://ai.azure.com/home)

## Azure resources (provisioned)

| Item | Value |
|------|--------|
| Subscription | Visual Studio Professional |
| Resource group | `rg-loginsights-dev` |
| Foundry account | `cog-a7fen2lryryp4` |
| Project | `loginsights-dev` |
| Agent | `log-insights-agent` |
| Region | North Central US |
| Project endpoint | `https://cog-a7fen2lryryp4.services.ai.azure.com/api/projects/loginsights-dev` |
| Agent playground | Open from [ai.azure.com](https://ai.azure.com) → project **loginsights-dev** → Agents → **log-insights-agent** |

## What the agent does

Hosted Python agent (Responses protocol) with tools:

| Tool | Purpose |
|------|---------|
| `filter_logs_tool` | Filter by level / component / user / keyword |
| `count_logs_tool` | Counts by level, component, or day |
| `health_summary_tool` | ERROR/WARN health index style summary |
| `semantic_search_tool` | Meaning-oriented search over messages |

Data source (env `LOG_DATA_SOURCE`):

- `auto` — Cosmos if configured, else sample CSV  
- `cosmos` — Azure Cosmos DB only  
- `csv` — bundled `data/sample_logs.csv`

## One-time model quota (required for chat)

Your **Visual Studio Professional** subscription currently has **0 TPM** for chat models (e.g. `gpt-5.4-mini`). The Foundry **project + agent are deployed**, but invokes need a model deployment.

1. Request quota: Azure Portal → **Quotas** (Cognitive Services / Azure OpenAI) or [https://aka.ms/oai/stuquotarequest](https://aka.ms/oai/stuquotarequest)  
   Ask for e.g. **GlobalStandard gpt-5.4-mini** (or `gpt-5-mini` / `gpt-4o-mini`) in a usable region.
2. Put the model back into `azure.yaml` under `services.ai-project.deployments` (example in file comments).
3. Run:

```powershell
cd foundryLogAgent\agent-framework-agent-with-local-tools-responses
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME "gpt-5.4-mini"
azd provision --no-prompt
azd deploy --no-prompt
```

**Note:** EPAM Production has model quota, but this account lacks `deployments/write` there. Prefer quota on VS Professional, or get Contributor + model access on a sub you can deploy to.

## Local commands

```powershell
# Auth
azd auth login
az login

cd foundryLogAgent\agent-framework-agent-with-local-tools-responses

# Status
azd ai project show
azd ai agent show log-insights-agent

# Invoke (after model is deployed)
azd ai agent invoke log-insights-agent "Show recent ERROR logs"
azd ai agent invoke log-insights-agent "What's the system health?"
azd ai agent invoke log-insights-agent "Find logs about connection problems"
```

## Redeploy after code changes

```powershell
azd deploy --no-prompt
```

## Layout

```text
foundryLogAgent/agent-framework-agent-with-local-tools-responses/
├── azure.yaml                 # Foundry agent + ai-project
├── src/.../main.py            # Hosted agent entry (tools + LLM)
├── src/.../log_tools.py       # Cosmos / CSV query helpers
└── src/.../data/sample_logs.csv
```

Related CLI POC (rule-based, no Foundry): `../stockAiApp/`.
