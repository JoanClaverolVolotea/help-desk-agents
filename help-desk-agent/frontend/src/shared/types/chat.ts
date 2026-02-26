export type ConversationId = string | null;

export interface TranscriptEntry {
  id: string;
  role: string;
  kind: string;
  agent?: string;
  text?: unknown;
}

export interface ChatEvent {
  kind?: string;
  agent?: string;
  text?: unknown;
  [key: string]: unknown;
}

export interface ChatStreamStartEvent {
  type: "start";
  conversation_id?: string;
  current_agent?: string;
  [key: string]: unknown;
}

export interface ChatStreamAgentUpdatedEvent {
  type: "agent_updated";
  agent?: string;
  [key: string]: unknown;
}

export interface ChatStreamTextDeltaEvent {
  type: "text_delta";
  delta?: string;
  [key: string]: unknown;
}

export interface ChatStreamEventPayloadEvent {
  type: "event";
  event?: ChatEvent;
  [key: string]: unknown;
}

export interface ChatStreamFinalEvent {
  type: "final";
  conversation_id?: string;
  current_agent?: string;
  [key: string]: unknown;
}

export interface ChatStreamErrorEvent {
  type: "error";
  detail?: string;
  [key: string]: unknown;
}

export interface ChatStreamUnknownEvent {
  type: string;
  [key: string]: unknown;
}

export type ChatStreamEvent =
  | ChatStreamStartEvent
  | ChatStreamAgentUpdatedEvent
  | ChatStreamTextDeltaEvent
  | ChatStreamEventPayloadEvent
  | ChatStreamFinalEvent
  | ChatStreamErrorEvent
  | ChatStreamUnknownEvent;

export interface ChatFinalPayload {
  conversation_id?: string;
  current_agent?: string;
}

export interface ChatResponse {
  conversation_id: string;
  current_agent: string;
  events: ChatEvent[];
}
