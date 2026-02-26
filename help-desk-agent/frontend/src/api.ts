import type {
  CategoryDetail,
  CategoryDraftPayload,
  CategorySummary,
  ChatFinalPayload,
  ChatResponse,
  ChatStreamEvent,
  ConversationId,
  ListResponse,
  MigrateUseCaseCategoryVersionPayload,
  ReseedDefaultsResponse,
  StepDefinition,
  TicketDetail,
  TicketFilters,
  TicketSummary,
  UseCaseDetail,
  UseCaseDraftPayload,
  UseCaseSummary,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

interface ConversationRequestPayload {
  message: string;
  conversation_id: ConversationId;
}

interface ConversationResetPayload {
  conversation_id: ConversationId;
}

interface CategoryResponse {
  category: CategoryDetail;
}

interface UseCaseResponse {
  use_case: UseCaseDetail;
}

interface TicketResponse {
  ticket: TicketDetail;
}

function apiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let payloadText = "Request failed.";
    try {
      const body = await response.json();
      payloadText = JSON.stringify(body);
    } catch {
      payloadText = await response.text();
    }
    throw new Error(payloadText);
  }

  return (await response.json()) as T;
}

export async function chat(message: string, conversationId: ConversationId): Promise<ChatResponse> {
  const payload: ConversationRequestPayload = {
    message,
    conversation_id: conversationId,
  };

  return request<ChatResponse>("/api/user/assistant/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function readErrorResponse(response: Response): Promise<string> {
  let payloadText = "Request failed.";
  try {
    const body = await response.json();
    payloadText = JSON.stringify(body);
  } catch {
    payloadText = await response.text();
  }
  return payloadText;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
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

export async function chatStream(
  message: string,
  conversationId: ConversationId,
  onEvent?: (event: ChatStreamEvent) => void,
): Promise<ChatFinalPayload | null> {
  const payload: ConversationRequestPayload = {
    message,
    conversation_id: conversationId,
  };

  const response = await fetch(`${apiBaseUrl()}/api/user/assistant/chat/stream`, {
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
      throw new Error(event.detail || "Streaming error.");
    }

    if (event.type === "final") {
      finalPayload = {
        conversation_id: event.conversation_id,
        current_agent: event.current_agent,
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

  return request<Record<string, unknown>>("/api/user/assistant/reset", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function adminAssistantChat(
  message: string,
  conversationId: ConversationId,
): Promise<ChatResponse> {
  const payload: ConversationRequestPayload = {
    message,
    conversation_id: conversationId,
  };

  return request<ChatResponse>("/api/admin/assistant/chat", {
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

  return request<Record<string, unknown>>("/api/admin/assistant/reset", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listTickets(
  filters: TicketFilters = {},
): Promise<ListResponse<TicketSummary>> {
  const params = new URLSearchParams();
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.conversationId) {
    params.set("conversation_id", filters.conversationId);
  }
  if (filters.externalTicketId) {
    params.set("external_ticket_id", filters.externalTicketId);
  }
  if (filters.useCaseId) {
    params.set("use_case_id", filters.useCaseId);
  }
  if (typeof filters.limit === "number") {
    params.set("limit", String(filters.limit));
  }
  if (typeof filters.offset === "number") {
    params.set("offset", String(filters.offset));
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request<ListResponse<TicketSummary>>(`/api/admin/tickets${suffix}`);
}

export async function getTicket(ticketId: string): Promise<TicketResponse> {
  return request<TicketResponse>(`/api/admin/tickets/${ticketId}`);
}

export async function reseedDefaults(): Promise<ReseedDefaultsResponse> {
  return request<ReseedDefaultsResponse>("/api/admin/bootstrap/reseed-defaults", {
    method: "POST",
    body: JSON.stringify({ confirm_token: "RESET_DEFAULTS" }),
  });
}

export async function listSteps(): Promise<ListResponse<StepDefinition>> {
  return request<ListResponse<StepDefinition>>("/api/admin/steps");
}

export async function listCategories(
  includeArchived = false,
): Promise<ListResponse<CategorySummary>> {
  return request<ListResponse<CategorySummary>>(
    `/api/admin/categories?include_archived=${includeArchived}`,
  );
}

export async function getCategory(categoryId: string): Promise<CategoryResponse> {
  return request<CategoryResponse>(`/api/admin/categories/${categoryId}`);
}

export async function createCategory(
  payload: CategoryDraftPayload,
): Promise<CategoryResponse> {
  return request<CategoryResponse>("/api/admin/categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCategoryDraft(
  categoryId: string,
  payload: CategoryDraftPayload,
): Promise<CategoryResponse> {
  return request<CategoryResponse>(`/api/admin/categories/${categoryId}/draft`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function publishCategory(categoryId: string): Promise<CategoryResponse> {
  return request<CategoryResponse>(`/api/admin/categories/${categoryId}/publish`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function archiveCategory(categoryId: string): Promise<CategoryResponse> {
  return request<CategoryResponse>(`/api/admin/categories/${categoryId}/archive`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function restoreCategory(categoryId: string): Promise<CategoryResponse> {
  return request<CategoryResponse>(`/api/admin/categories/${categoryId}/restore`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function listUseCases(
  includeArchived = false,
): Promise<ListResponse<UseCaseSummary>> {
  return request<ListResponse<UseCaseSummary>>(
    `/api/admin/use-cases?include_archived=${includeArchived}`,
  );
}

export async function getUseCase(useCaseId: string): Promise<UseCaseResponse> {
  return request<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}`);
}

export async function createUseCase(payload: UseCaseDraftPayload): Promise<UseCaseResponse> {
  return request<UseCaseResponse>("/api/admin/use-cases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateUseCaseDraft(
  useCaseId: string,
  payload: { category_id: string; definition: UseCaseDraftPayload["definition"] },
): Promise<UseCaseResponse> {
  return request<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}/draft`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function publishUseCase(useCaseId: string): Promise<UseCaseResponse> {
  return request<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}/publish`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function archiveUseCase(useCaseId: string): Promise<UseCaseResponse> {
  return request<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}/archive`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function restoreUseCase(useCaseId: string): Promise<UseCaseResponse> {
  return request<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}/restore`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function migrateUseCaseCategoryVersion(
  useCaseId: string,
  payload: MigrateUseCaseCategoryVersionPayload,
): Promise<UseCaseResponse> {
  return request<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}/migrate-category-version`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function readableError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}
