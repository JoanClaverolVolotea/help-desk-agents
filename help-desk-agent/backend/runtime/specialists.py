from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from backend.domain.models import PublishedUseCaseSummary
from backend.workflows.tools import build_use_case_workflow_tool


def build_specialist_agent(use_case: PublishedUseCaseSummary) -> Agent[Any]:
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


def specialist_handoff_tool_name(use_case: PublishedUseCaseSummary) -> str:
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
