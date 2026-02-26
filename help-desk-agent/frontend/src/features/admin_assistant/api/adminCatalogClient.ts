import { requestJson } from "../../../shared/api/httpClient";
import type {
  ApproveTicketPayload,
  CategoryDetail,
  CategoryDraftPayload,
  CategorySummary,
  ListResponse,
  MigrateUseCaseCategoryVersionPayload,
  RejectTicketPayload,
  ReseedDefaultsResponse,
  StepDefinition,
  TicketDetail,
  TicketFilters,
  TicketSummary,
  UseCaseDetail,
  UseCaseDraftPayload,
  UseCaseSummary,
} from "../types";

interface CategoryResponse {
  category: CategoryDetail;
}

interface UseCaseResponse {
  use_case: UseCaseDetail;
}

interface TicketResponse {
  ticket: TicketDetail;
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
  return requestJson<ListResponse<TicketSummary>>(`/api/admin/tickets${suffix}`);
}

export async function getTicket(ticketId: string): Promise<TicketResponse> {
  return requestJson<TicketResponse>(`/api/admin/tickets/${ticketId}`);
}

export async function approveTicket(
  ticketId: string,
  payload: ApproveTicketPayload,
): Promise<TicketResponse> {
  return requestJson<TicketResponse>(`/api/admin/tickets/${ticketId}/approve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function rejectTicket(
  ticketId: string,
  payload: RejectTicketPayload,
): Promise<TicketResponse> {
  return requestJson<TicketResponse>(`/api/admin/tickets/${ticketId}/reject`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function reseedDefaults(): Promise<ReseedDefaultsResponse> {
  return requestJson<ReseedDefaultsResponse>("/api/admin/bootstrap/reseed-defaults", {
    method: "POST",
    body: JSON.stringify({ confirm_token: "RESET_DEFAULTS" }),
  });
}

export async function listSteps(): Promise<ListResponse<StepDefinition>> {
  return requestJson<ListResponse<StepDefinition>>("/api/admin/steps");
}

export async function listCategories(
  includeArchived = false,
): Promise<ListResponse<CategorySummary>> {
  return requestJson<ListResponse<CategorySummary>>(
    `/api/admin/categories?include_archived=${includeArchived}`,
  );
}

export async function getCategory(categoryId: string): Promise<CategoryResponse> {
  return requestJson<CategoryResponse>(`/api/admin/categories/${categoryId}`);
}

export async function createCategory(
  payload: CategoryDraftPayload,
): Promise<CategoryResponse> {
  return requestJson<CategoryResponse>("/api/admin/categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCategoryDraft(
  categoryId: string,
  payload: CategoryDraftPayload,
): Promise<CategoryResponse> {
  return requestJson<CategoryResponse>(`/api/admin/categories/${categoryId}/draft`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function publishCategory(categoryId: string): Promise<CategoryResponse> {
  return requestJson<CategoryResponse>(`/api/admin/categories/${categoryId}/publish`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function archiveCategory(categoryId: string): Promise<CategoryResponse> {
  return requestJson<CategoryResponse>(`/api/admin/categories/${categoryId}/archive`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function restoreCategory(categoryId: string): Promise<CategoryResponse> {
  return requestJson<CategoryResponse>(`/api/admin/categories/${categoryId}/restore`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function listUseCases(
  includeArchived = false,
): Promise<ListResponse<UseCaseSummary>> {
  return requestJson<ListResponse<UseCaseSummary>>(
    `/api/admin/use-cases?include_archived=${includeArchived}`,
  );
}

export async function getUseCase(useCaseId: string): Promise<UseCaseResponse> {
  return requestJson<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}`);
}

export async function createUseCase(payload: UseCaseDraftPayload): Promise<UseCaseResponse> {
  return requestJson<UseCaseResponse>("/api/admin/use-cases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateUseCaseDraft(
  useCaseId: string,
  payload: { category_id: string; definition: UseCaseDraftPayload["definition"] },
): Promise<UseCaseResponse> {
  return requestJson<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}/draft`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function publishUseCase(useCaseId: string): Promise<UseCaseResponse> {
  return requestJson<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}/publish`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function archiveUseCase(useCaseId: string): Promise<UseCaseResponse> {
  return requestJson<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}/archive`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function restoreUseCase(useCaseId: string): Promise<UseCaseResponse> {
  return requestJson<UseCaseResponse>(`/api/admin/use-cases/${useCaseId}/restore`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function migrateUseCaseCategoryVersion(
  useCaseId: string,
  payload: MigrateUseCaseCategoryVersionPayload,
): Promise<UseCaseResponse> {
  return requestJson<UseCaseResponse>(
    `/api/admin/use-cases/${useCaseId}/migrate-category-version`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
