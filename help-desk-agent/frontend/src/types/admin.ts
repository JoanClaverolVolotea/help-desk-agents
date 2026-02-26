export type TicketStatus = "open" | "in_progress" | "resolved" | string;

export interface ListResponse<T> {
  items: T[];
}

export interface StepDefinition {
  step_id: string;
}

export interface WorkflowStep {
  step_id: string;
  params: Record<string, unknown>;
}

export interface CategoryDefinition {
  display_name: string;
  description: string;
  allowed_step_ids: string[];
  default_handoff_description: string;
  default_routing_description: string;
  default_required_fields: string[];
  default_steps: WorkflowStep[];
}

export interface CategorySummary {
  category_id: string;
  display_name: string;
  archived: boolean;
  draft_version_number: number | null;
  published_version_number: number | null;
  slug?: string;
}

export interface CategoryDetail extends CategorySummary {
  draft_definition: CategoryDefinition | null;
  published_definition: CategoryDefinition | null;
}

export interface UseCaseDefinition {
  display_name: string;
  handoff_description: string;
  routing_description: string;
  required_fields: string[];
  steps: WorkflowStep[];
}

export interface UseCaseSummary {
  use_case_id: string;
  category_id: string | null;
  display_name: string;
  archived: boolean;
  draft_version_number: number | null;
  published_version_number: number | null;
  is_system_default: boolean;
  slug?: string;
}

export interface UseCaseDetail extends UseCaseSummary {
  draft_definition: UseCaseDefinition | null;
  published_definition: UseCaseDefinition | null;
}

export interface CategoryDraftPayload {
  slug?: string;
  definition: {
    display_name: string;
    description: string;
    allowed_step_ids: string[];
    default_handoff_description: string;
    default_routing_description: string;
    default_required_fields: string[];
    default_steps: WorkflowStep[];
  };
}

export interface UseCaseDraftPayload {
  slug?: string;
  category_id: string;
  definition: {
    display_name: string;
    handoff_description: string;
    routing_description: string;
    required_fields: string[];
    steps: WorkflowStep[];
  };
}

export interface TicketSummary {
  ticket_id: string;
  external_ticket_id: string | null;
  use_case_id: string | null;
  use_case_display_name: string | null;
  conversation_id: string | null;
  status: TicketStatus;
  created_at: string;
}

export interface TicketStatusHistoryItem {
  status: TicketStatus;
  changed_at: string;
  reason: string | null;
}

export interface TicketFieldItem {
  field_name: string;
  field_value: string;
  source: string;
  is_required: boolean;
}

export interface TicketWorkflowStepItem {
  step_order: number;
  step_id: string;
  output_text: string;
}

export interface TicketEventItem {
  event_type: string;
  agent_name: string | null;
  created_at: string;
  payload_json: string;
}

export interface TicketDetail extends TicketSummary {
  resolved_at: string | null;
  ticket_context: string;
  error_message: string | null;
  status_history: TicketStatusHistoryItem[];
  fields: TicketFieldItem[];
  steps: TicketWorkflowStepItem[];
  events: TicketEventItem[];
}

export interface TicketFilters {
  status?: string;
  conversationId?: string;
  externalTicketId?: string;
  useCaseId?: string;
  limit?: number;
  offset?: number;
}

export interface ReseedDefaultsResponse {
  deleted_counts: {
    tickets: number;
    use_cases: number;
    categories: number;
  };
  seeded_counts: {
    categories: number;
    use_cases: number;
  };
}

export interface MigrateUseCaseCategoryVersionPayload {
  category_id: string;
  category_version_number: number | null;
}
