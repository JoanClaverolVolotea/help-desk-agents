from __future__ import annotations

import asyncio
import pathlib
import sys
import uuid
from typing import Any

CURRENT_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(1, str(REPO_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(2, str(CURRENT_DIR))

from help_desk_agents import triage_agent  # noqa: E402

from agents import (  # noqa: E402
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    trace,
)
from examples.auto_mode import input_with_fallback, is_auto_mode  # noqa: E402


def _default_sample_ticket() -> str:
    return (
        "Reset de acceso Ecrew: USDV-176285. "
        "Francois Emeriau has a log in problem into eCrew. "
        "Tipo de sol: Fix an account issue."
    )


async def main() -> None:
    current_agent: Agent[Any] = triage_agent
    input_items: list[TResponseInputItem] = []
    auto_mode = is_auto_mode()
    conversation_id = uuid.uuid4().hex[:16]

    while True:
        user_input = input_with_fallback(
            "Enter help desk ticket details (or 'exit'): ",
            _default_sample_ticket(),
        )
        if user_input.strip().lower() in {"exit", "quit"}:
            print("Exiting help desk agent demo.")
            break

        with trace("Help desk multi-agent demo", group_id=conversation_id):
            input_items.append({"content": user_input, "role": "user"})
            result = await Runner.run(current_agent, input_items)

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    text = ItemHelpers.text_message_output(new_item)
                    if text:
                        print(f"{agent_name}: {text}")
                elif isinstance(new_item, HandoffOutputItem):
                    print(
                        "Handed off from "
                        f"{new_item.source_agent.name} to {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    tool_name = getattr(new_item.raw_item, "name", new_item.__class__.__name__)
                    print(f"{agent_name}: Calling tool {tool_name}")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"{agent_name}: Tool output: {new_item.output}")
                else:
                    print(f"{agent_name}: Skipping {new_item.__class__.__name__}")

            input_items = result.to_input_list()
            current_agent = result.last_agent

        if auto_mode:
            break


if __name__ == "__main__":
    asyncio.run(main())
