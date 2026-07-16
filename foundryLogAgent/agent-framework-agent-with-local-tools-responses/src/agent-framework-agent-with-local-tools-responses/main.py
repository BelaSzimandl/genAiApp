# Copyright (c) Microsoft. All rights reserved.
"""Foundry hosted Log Insights agent — LLM + Cosmos log tools."""

from __future__ import annotations

import os
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field

from log_tools import (
    count_logs,
    filter_logs,
    health_summary,
    semantic_search_logs,
)

load_dotenv()

INSTRUCTIONS = """You are the AI Log Insights assistant for security and operations monitoring.

You help analysts query structured monitoring logs (CASB, PAM, VulnScanner, etc.) using tools.
Always prefer tools over guessing. Summarize results clearly for non-SQL users.

Supported data:
- Fields: Timestamp, system_name, component, log_level, corr_id, user_ID, message
- Components often include CASB, PAM, VulnScanner
- Levels: DEBUG, INFO, WARN, ERROR, CRITICAL

When users ask about meaning or vague issues (timeouts, threats, suspicious activity), use semantic_search_logs.
When they ask for counts, trends, or health, use count_logs or health_summary.
When they ask for specific filters (ERROR logs, ADMIN activity), use filter_logs.

Keep answers concise. Include counts and key messages. Suggest follow-up questions when useful.
"""


@tool(approval_mode="never_require")
def filter_logs_tool(
    log_level: Annotated[str | None, Field(description="Log level filter e.g. ERROR, WARN, INFO")] = None,
    component: Annotated[str | None, Field(description="Component filter e.g. CASB, PAM, VulnScanner")] = None,
    user_id: Annotated[str | None, Field(description="User ID filter e.g. ADMIN")] = None,
    keyword: Annotated[str | None, Field(description="Keyword to match in message text")] = None,
    max_rows: Annotated[int, Field(description="Max rows to return")] = 10,
) -> str:
    """Filter structured logs by level, component, user, or message keyword."""
    return filter_logs(
        log_level=log_level,
        component=component,
        user_id=user_id,
        keyword=keyword,
        max_rows=max_rows,
    )


@tool(approval_mode="never_require")
def count_logs_tool(
    group_by: Annotated[
        str,
        Field(description="Group by: log_level, component, or time (daily buckets)"),
    ] = "log_level",
) -> str:
    """Aggregate log counts by level, component, or day."""
    return count_logs(group_by=group_by)


@tool(approval_mode="never_require")
def health_summary_tool() -> str:
    """Summarize overall system health from ERROR/WARN rates (monitoring index style)."""
    return health_summary()


@tool(approval_mode="never_require")
def semantic_search_tool(
    query: Annotated[str, Field(description="Natural language description of logs to find")],
    top_k: Annotated[int, Field(description="Number of similar logs to return")] = 5,
) -> str:
    """Semantic / vector-style search over log messages by meaning."""
    return semantic_search_logs(query=query, top_k=top_k)


def main() -> None:
    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT") or os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    model = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if not endpoint or not model:
        raise RuntimeError(
            "FOUNDRY_PROJECT_ENDPOINT (or AZURE_AI_PROJECT_ENDPOINT) and "
            "AZURE_AI_MODEL_DEPLOYMENT_NAME must be set"
        )

    client = FoundryChatClient(
        project_endpoint=endpoint,
        model=model,
        credential=DefaultAzureCredential(),
    )

    agent = Agent(
        client=client,
        instructions=INSTRUCTIONS,
        tools=[filter_logs_tool, count_logs_tool, health_summary_tool, semantic_search_tool],
        default_options={"store": False},
    )

    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
