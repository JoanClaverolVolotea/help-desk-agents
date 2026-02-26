from __future__ import annotations

from typing import Any

from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX


def build_triage_agent(specialists: list[Agent[Any]]) -> Agent[Any]:
    triage_agent = Agent(
        name="Tech Team Assistant Triage",
        handoff_description="Routes technical admin requests to the right specialist.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You triage technical admin requests.

- Handoff to Category Creator Specialist for creating/publishing new categories.
- Handoff to Category Lifecycle Specialist for inspection/maintenance.
- Ask clarifying questions when intent is ambiguous.
- Reply only in the language of the user's latest message.
- Do not include translations or bilingual sections.
""",
        handoffs=[],
    )
    triage_agent.handoffs.extend(specialists)
    for specialist in specialists:
        specialist.handoffs.append(triage_agent)
    return triage_agent
