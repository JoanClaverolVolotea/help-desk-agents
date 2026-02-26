import { requestJson } from "../../../shared/api/httpClient";
import type { ChatResponse, ConversationId } from "../../../shared/types";

interface ConversationRequestPayload {
  message: string;
  conversation_id: ConversationId;
}

interface ConversationResetPayload {
  conversation_id: ConversationId;
}

export async function adminAssistantChat(
  message: string,
  conversationId: ConversationId,
): Promise<ChatResponse> {
  const payload: ConversationRequestPayload = {
    message,
    conversation_id: conversationId,
  };

  return requestJson<ChatResponse>("/api/admin/assistant/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function resetAdminAssistantConversation(
  conversationId: ConversationId,
): Promise<Record<string, unknown>> {
  const payload: ConversationResetPayload = {
    conversation_id: conversationId,
  };

  return requestJson<Record<string, unknown>>("/api/admin/assistant/reset", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
