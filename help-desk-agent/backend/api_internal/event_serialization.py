from __future__ import annotations

import json
from typing import Any

from agents import (
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    ToolCallItem,
    ToolCallOutputItem,
)
from backend.api.schemas.chat import ChatEvent
from backend.domain.language_policy import translate_backend_text


def serialize_tool_output(output: Any) -> str:
    if isinstance(output, str):
        return output
    try:
        return json.dumps(output, ensure_ascii=True)
    except TypeError:
        return str(output)


def event_from_item(item: Any, language: str) -> ChatEvent | None:
    agent_name = item.agent.name
    if isinstance(item, MessageOutputItem):
        text = ItemHelpers.text_message_output(item)
        if not text:
            return None
        return ChatEvent(kind="message", agent=agent_name, text=text)
    if isinstance(item, HandoffOutputItem):
        return ChatEvent(
            kind="handoff",
            agent=agent_name,
            text=translate_backend_text(
                "handoff_event",
                language,
                source=item.source_agent.name,
                target=item.target_agent.name,
            ),
        )
    if isinstance(item, ToolCallItem):
        tool_name = getattr(item.raw_item, "name", item.__class__.__name__)
        return ChatEvent(
            kind="tool_call",
            agent=agent_name,
            text=translate_backend_text("tool_call_event", language, tool_name=tool_name),
        )
    if isinstance(item, ToolCallOutputItem):
        return ChatEvent(
            kind="tool_output",
            agent=agent_name,
            text=serialize_tool_output(item.output),
        )
    return ChatEvent(
        kind="info",
        agent=agent_name,
        text=translate_backend_text(
            "skip_event",
            language,
            item_class=item.__class__.__name__,
        ),
    )


def ndjson_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True) + "\n"
