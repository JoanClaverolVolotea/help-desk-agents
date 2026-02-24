from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Any

from models import PublishedUseCaseSummary
from tools import build_use_case_workflow_tool

from agents import Agent, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX


@dataclass
class RuntimeSnapshot:
    snapshot_id: str
    triage_agent: Agent[Any]
    specialists_by_use_case_id: dict[str, Agent[Any]]
    published_use_cases: list[PublishedUseCaseSummary]


def build_runtime_snapshot(published_use_cases: list[PublishedUseCaseSummary]) -> RuntimeSnapshot:
    specialists_by_use_case_id: dict[str, Agent[Any]] = {}
    triage_handoffs = []

    for use_case in published_use_cases:
        specialist = _build_specialist_agent(use_case)
        specialists_by_use_case_id[use_case.use_case_id] = specialist
        triage_handoffs.append(
            handoff(
                specialist,
                tool_name_override=_specialist_handoff_tool_name(use_case),
            )
        )

    triage_agent = _build_triage_agent(published_use_cases, triage_handoffs)
    for specialist in specialists_by_use_case_id.values():
        specialist.handoffs.append(triage_agent)

    return RuntimeSnapshot(
        snapshot_id=uuid.uuid4().hex[:16],
        triage_agent=triage_agent,
        specialists_by_use_case_id=specialists_by_use_case_id,
        published_use_cases=published_use_cases,
    )


def _build_specialist_agent(use_case: PublishedUseCaseSummary) -> Agent[Any]:
    required_fields = ", ".join(use_case.definition.required_fields) or "none"

    instructions = f"""{RECOMMENDED_PROMPT_PREFIX}
You are the specialist agent for the use case: {use_case.display_name}.

Context:
- Routing description: {use_case.definition.routing_description}
- Required fields: {required_fields}

Routine:
1. Review the latest user ticket text.
2. If any required field is missing, ask concise follow-up questions and wait for user response.
3. When ready, call execute_use_case_workflow exactly once.
4. Pass the full ticket text as ticket_context.
5. Pass a compact JSON object with collected required fields in field_values_json.
6. Return a concise final answer.

Rules:
- Use tool output as source of truth.
- If the ticket does not match this use case, handoff back to triage.
- Reply only in the language of the user's latest message.
- Do not include translations or bilingual sections.
"""

    specialist = Agent(
        name=f"{use_case.display_name} Specialist",
        handoff_description=use_case.definition.handoff_description,
        instructions=instructions,
        tools=[build_use_case_workflow_tool(use_case)],
    )
    return specialist


def _build_triage_agent(
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


def _specialist_handoff_tool_name(use_case: PublishedUseCaseSummary) -> str:
    max_length = 64
    prefix = "transfer_to_"
    separator = "_"
    suffix = hashlib.sha1(use_case.use_case_id.encode("utf-8")).hexdigest()[:10]
    slug_part = _normalize_for_tool_name(use_case.slug)
    slug_limit = max_length - len(prefix) - len(separator) - len(suffix)
    safe_slug = slug_part[:slug_limit].rstrip("_") or "use_case"
    return f"{prefix}{safe_slug}{separator}{suffix}"


def _normalize_for_tool_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    cleaned = re.sub(r"[^a-z0-9_]+", "_", ascii_only)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "use_case"
