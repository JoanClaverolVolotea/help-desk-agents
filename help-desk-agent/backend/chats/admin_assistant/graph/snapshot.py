from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from agents import Agent
from backend.chats.admin_assistant.graph.specialists import build_specialists
from backend.chats.admin_assistant.graph.triage import build_triage_agent


@dataclass
class RuntimeSnapshot:
    snapshot_id: str
    triage_agent: Agent[Any]


def build_runtime_snapshot() -> RuntimeSnapshot:
    specialists = build_specialists()
    triage_agent = build_triage_agent(specialists)

    return RuntimeSnapshot(
        snapshot_id=uuid.uuid4().hex[:16],
        triage_agent=triage_agent,
    )
