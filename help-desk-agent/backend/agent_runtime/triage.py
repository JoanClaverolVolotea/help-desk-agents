from __future__ import annotations

from typing import Any

from models import PublishedUseCaseSummary

from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX


def build_triage_agent(
    published_use_cases: list[PublishedUseCaseSummary],
    triage_handoffs: list[Any],
) -> Agent[Any]:
    if not published_use_cases:
        instructions = f"""{RECOMMENDED_PROMPT_PREFIX}
You are the Help Desk Triage Agent.

There are no published use cases.
Explain this clearly and ask the operator to escalate to an administrator.
Do not invent workflows.
"""
        return Agent(
            name="Help Desk Triage Agent",
            handoff_description="Routes tickets to use-case specialists.",
            instructions=instructions,
            handoffs=[],
        )

    routing_lines = "\n".join(
        [
            f"- {case.display_name}: {case.definition.routing_description}"
            for case in published_use_cases
        ]
    )
    instructions = f"""{RECOMMENDED_PROMPT_PREFIX}
You are the Help Desk Triage Agent.

Published use cases:
{routing_lines}

Routing routine:
1. Analyze the latest ticket request.
2. Select the best matching specialist and handoff.
3. If ambiguous, ask clarifying questions before handoff.
4. If nothing matches, explain no suitable use case and ask for additional context.

Rules:
- Use only available specialists.
- Do not execute specialist workflows yourself.
- Reply only in the language of the user's latest message.
- Do not include translations or bilingual sections.
"""

    triage_agent = Agent(
        name="Help Desk Triage Agent",
        handoff_description="Routes tickets to use-case specialists.",
        instructions=instructions,
        handoffs=[],
    )
    triage_agent.handoffs.extend(triage_handoffs)
    return triage_agent
