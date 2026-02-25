const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function apiBaseUrl() {
  return import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

async function request(path, options = {}) {
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

  return response.json();
}

export async function chat(message, conversationId) {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
}

async function readErrorResponse(response) {
  let payloadText = "Request failed.";
  try {
    const body = await response.json();
    payloadText = JSON.stringify(body);
  } catch {
    payloadText = await response.text();
  }
  return payloadText;
}

function parseNdjsonLines(chunk, onLine) {
  const lines = chunk.split("\n");
  const remainder = lines.pop() ?? "";
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    let parsed;
    try {
      parsed = JSON.parse(trimmed);
    } catch {
      continue;
    }
    onLine(parsed);
  }
  return remainder;
}

export async function chatStream(message, conversationId, onEvent) {
  const response = await fetch(`${apiBaseUrl()}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
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
  let finalPayload = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    const chunk = remainder + decoder.decode(value, { stream: true });
    remainder = parseNdjsonLines(chunk, (event) => {
      onEvent?.(event);
      if (event?.type === "error") {
        throw new Error(event.detail || "Streaming error.");
      }
      if (event?.type === "final") {
        finalPayload = {
          conversation_id: event.conversation_id,
          current_agent: event.current_agent,
        };
      }
    });
  }

  const finalChunk = remainder + decoder.decode();
  parseNdjsonLines(finalChunk, (event) => {
    onEvent?.(event);
    if (event?.type === "error") {
      throw new Error(event.detail || "Streaming error.");
    }
    if (event?.type === "final") {
      finalPayload = {
        conversation_id: event.conversation_id,
        current_agent: event.current_agent,
      };
    }
  });

  return finalPayload;
}

export async function resetConversation(conversationId) {
  return request("/api/reset", {
    method: "POST",
    body: JSON.stringify({ conversation_id: conversationId }),
  });
}

export async function adminAssistantChat(message, conversationId) {
  return request("/api/admin/assistant/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
}

export async function resetAdminAssistantConversation(conversationId) {
  return request("/api/admin/assistant/reset", {
    method: "POST",
    body: JSON.stringify({ conversation_id: conversationId }),
  });
}

export async function listTickets(filters = {}) {
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
  return request(`/api/admin/tickets${suffix}`);
}

export async function getTicket(ticketId) {
  return request(`/api/admin/tickets/${ticketId}`);
}

export async function listSteps() {
  return request("/api/admin/steps");
}

export async function listCategories(includeArchived = false) {
  return request(`/api/admin/categories?include_archived=${includeArchived}`);
}

export async function getCategory(categoryId) {
  return request(`/api/admin/categories/${categoryId}`);
}

export async function createCategory(payload) {
  return request("/api/admin/categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCategoryDraft(categoryId, payload) {
  return request(`/api/admin/categories/${categoryId}/draft`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function publishCategory(categoryId) {
  return request(`/api/admin/categories/${categoryId}/publish`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function archiveCategory(categoryId) {
  return request(`/api/admin/categories/${categoryId}/archive`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function restoreCategory(categoryId) {
  return request(`/api/admin/categories/${categoryId}/restore`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function listUseCases(includeArchived = false) {
  return request(`/api/admin/use-cases?include_archived=${includeArchived}`);
}

export async function getUseCase(useCaseId) {
  return request(`/api/admin/use-cases/${useCaseId}`);
}

export async function createUseCase(payload) {
  return request("/api/admin/use-cases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateUseCaseDraft(useCaseId, payload) {
  return request(`/api/admin/use-cases/${useCaseId}/draft`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function publishUseCase(useCaseId) {
  return request(`/api/admin/use-cases/${useCaseId}/publish`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function archiveUseCase(useCaseId) {
  return request(`/api/admin/use-cases/${useCaseId}/archive`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function restoreUseCase(useCaseId) {
  return request(`/api/admin/use-cases/${useCaseId}/restore`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function migrateUseCaseCategoryVersion(useCaseId, payload) {
  return request(`/api/admin/use-cases/${useCaseId}/migrate-category-version`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function readableError(error) {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}
