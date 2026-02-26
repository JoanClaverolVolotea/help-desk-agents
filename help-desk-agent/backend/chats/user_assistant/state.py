from __future__ import annotations

from backend.chats.shared.state import ConversationState
from backend.chats.user_assistant.graph.snapshot import RuntimeSnapshot

USER_ASSISTANT_CONVERSATIONS: dict[str, ConversationState] = {}


def ensure_user_assistant_state(
    conversation_id: str,
    runtime_snapshot: RuntimeSnapshot,
) -> ConversationState:
    state = USER_ASSISTANT_CONVERSATIONS.get(conversation_id)
    if state is None:
        state = ConversationState(
            snapshot_id=runtime_snapshot.snapshot_id,
            current_agent=runtime_snapshot.triage_agent,
        )
        USER_ASSISTANT_CONVERSATIONS[conversation_id] = state
    return state
