from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from models import PublishedUseCaseSummary

from agent_runtime.specialists import build_specialist_agent, specialist_handoff_tool_name
from agent_runtime.triage import build_triage_agent
from agents import Agent, handoff


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
        specialist = build_specialist_agent(use_case)
        specialists_by_use_case_id[use_case.use_case_id] = specialist
        triage_handoffs.append(
            handoff(
                specialist,
                tool_name_override=specialist_handoff_tool_name(use_case),
            )
        )

    triage_agent = build_triage_agent(published_use_cases, triage_handoffs)
    for specialist in specialists_by_use_case_id.values():
        specialist.handoffs.append(triage_agent)

    return RuntimeSnapshot(
        snapshot_id=uuid.uuid4().hex[:16],
        triage_agent=triage_agent,
        specialists_by_use_case_id=specialists_by_use_case_id,
        published_use_cases=published_use_cases,
    )
