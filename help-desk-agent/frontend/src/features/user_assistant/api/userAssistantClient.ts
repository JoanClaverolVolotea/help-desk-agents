import { buildApiUrl, isRecord, readErrorResponse, requestJson } from "../../../shared/api/httpClient";
import type {
  ChatFinalPayload,
  ChatResponse,
  ChatStreamEvent,
  ConversationId,
} from "../../../shared/types";

interface ConversationRequestPayload {
  message: string;
  conversation_id: ConversationId;
}

interface ConversationResetPayload {
  conversation_id: ConversationId;
}

function parseNdjsonLines(
  chunk: string,
  onLine: (line: Record<string, unknown>) => void,
): string {
  const lines = chunk.split("\n");
  const remainder = lines.pop() ?? "";
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(trimmed);
    } catch {
      continue;
    }
    if (isRecord(parsed)) {
      onLine(parsed);
    }
  }
  return remainder;
}

export async function chat(
  message: string,
  conversationId: ConversationId,
): Promise<ChatResponse> {
  const payload: ConversationRequestPayload = {
    message,
    conversation_id: conversationId,
  };

  return requestJson<ChatResponse>("/api/user/assistant/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function chatStream(
  message: string,
  conversationId: ConversationId,
  onEvent?: (event: ChatStreamEvent) => void,
): Promise<ChatFinalPayload | null> {
  const payload: ConversationRequestPayload = {
    message,
    conversation_id: conversationId,
  };

  const response = await fetch(buildApiUrl("/api/user/assistant/chat/stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await readErrorResponse(response));
  }
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let remainder = "";
  let finalPayload: ChatFinalPayload | null = null;

  const processEvent = (rawEvent: Record<string, unknown>): void => {
    const event = rawEvent as ChatStreamEvent;
    onEvent?.(event);

    if (event.type === "error") {
      const detail = typeof rawEvent.detail === "string" ? rawEvent.detail : "Streaming error.";
      throw new Error(detail);
    }

    if (event.type === "final") {
      finalPayload = {
        conversation_id:
          typeof rawEvent.conversation_id === "string" ? rawEvent.conversation_id : undefined,
        current_agent:
          typeof rawEvent.current_agent === "string" ? rawEvent.current_agent : undefined,
      };
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    const chunk = remainder + decoder.decode(value, { stream: true });
    remainder = parseNdjsonLines(chunk, processEvent);
  }

  const finalChunk = remainder + decoder.decode();
  parseNdjsonLines(finalChunk, processEvent);

  return finalPayload;
}

export async function resetConversation(
  conversationId: ConversationId,
): Promise<Record<string, unknown>> {
  const payload: ConversationResetPayload = {
    conversation_id: conversationId,
  };

  return requestJson<Record<string, unknown>>("/api/user/assistant/reset", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
