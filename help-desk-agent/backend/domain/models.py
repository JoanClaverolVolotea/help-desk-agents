from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VersionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class UseCaseStep(BaseModel):
    step_id: str
    params: dict[str, str] = Field(default_factory=dict)

    @field_validator("step_id")
    @classmethod
    def validate_step_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("step_id must not be empty")
        return normalized


class StepCatalogItem(BaseModel):
    step_id: str
    description: str


class CategoryDefinition(BaseModel):
    display_name: str
    description: str
    allowed_step_ids: list[str] = Field(default_factory=list)
    default_handoff_description: str
    default_routing_description: str
    default_required_fields: list[str] = Field(default_factory=list)
    default_steps: list[UseCaseStep] = Field(default_factory=list)

    @field_validator(
        "display_name",
        "description",
        "default_handoff_description",
        "default_routing_description",
    )
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field must not be empty")
        return normalized


class CategoryDefinitionDraft(CategoryDefinition):
    pass


class CategoryDefinitionPublished(CategoryDefinition):
    version_number: int


class CategoryDefinitionInput(CategoryDefinition):
    pass


class CategoryListItem(BaseModel):
    category_id: str
    slug: str
    display_name: str
    draft_version_number: int | None = None
    published_version_number: int | None = None
    archived: bool
    updated_at: str


class CategoryDetail(BaseModel):
    category_id: str
    slug: str
    display_name: str
    draft_version_number: int | None = None
    published_version_number: int | None = None
    draft_definition: CategoryDefinitionDraft | None = None
    published_definition: CategoryDefinitionPublished | None = None
    archived: bool
    created_at: str
    updated_at: str


class CreateCategoryRequest(BaseModel):
    slug: str | None = None
    definition: CategoryDefinitionInput


class UpdateCategoryDraftRequest(BaseModel):
    definition: CategoryDefinitionInput


class CategoryListResponse(BaseModel):
    items: list[CategoryListItem]


class CategoryDetailResponse(BaseModel):
    category: CategoryDetail


class StepCatalogResponse(BaseModel):
    items: list[StepCatalogItem]


class ArchiveRestoreResponse(BaseModel):
    success: bool
    entity_id: str
    archived: bool


class UseCaseDefinition(BaseModel):
    display_name: str
    handoff_description: str
    routing_description: str
    required_fields: list[str] = Field(default_factory=list)
    steps: list[UseCaseStep] = Field(default_factory=list)

    @field_validator("display_name", "handoff_description", "routing_description")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field must not be empty")
        return normalized


class UseCaseDefinitionDraft(UseCaseDefinition):
    pass


class UseCaseDefinitionPublished(UseCaseDefinition):
    version_number: int


class UseCaseDefinitionInput(UseCaseDefinition):
    pass


class PublishedUseCaseSummary(BaseModel):
    use_case_id: str
    slug: str
    display_name: str
    category_id: str | None = None
    category_version_number: int | None = None
    version_number: int
    definition: UseCaseDefinitionPublished


class UseCaseListItem(BaseModel):
    use_case_id: str
    slug: str
    display_name: str
    category_id: str | None = None
    category_version_number: int | None = None
    is_system_default: bool = False
    is_detached: bool
    draft_version_number: int | None = None
    published_version_number: int | None = None
    archived: bool
    updated_at: str


class UseCaseDetail(BaseModel):
    use_case_id: str
    slug: str
    display_name: str
    category_id: str | None = None
    category_version_number: int | None = None
    is_system_default: bool = False
    is_detached: bool
    draft_version_number: int | None = None
    published_version_number: int | None = None
    draft_definition: UseCaseDefinitionDraft | None = None
    published_definition: UseCaseDefinitionPublished | None = None
    archived: bool
    created_at: str
    updated_at: str


class CreateUseCaseRequest(BaseModel):
    slug: str | None = None
    category_id: str
    definition: UseCaseDefinitionInput


class UpdateUseCaseDraftRequest(BaseModel):
    category_id: str
    definition: UseCaseDefinitionInput


class MigrateCategoryVersionRequest(BaseModel):
    category_id: str
    category_version_number: int


class CreateUseCaseResponse(BaseModel):
    use_case: UseCaseDetail


class PublishUseCaseResponse(BaseModel):
    use_case: UseCaseDetail


class UseCaseListResponse(BaseModel):
    items: list[UseCaseListItem]


class UseCaseDetailResponse(BaseModel):
    use_case: UseCaseDetail


class ReseedDefaultsRequest(BaseModel):
    confirm_token: Literal["RESET_DEFAULTS"]


class ReseedDeletedCounts(BaseModel):
    tickets: int
    use_cases: int
    categories: int


class ReseedSeededCounts(BaseModel):
    categories: int
    use_cases: int


class ReseedDefaultsResponse(BaseModel):
    success: bool
    deleted_counts: ReseedDeletedCounts
    seeded_counts: ReseedSeededCounts


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class TicketFieldSource(str, Enum):
    PROVIDED = "provided"
    DERIVED = "derived"
    MISSING = "missing"


class TicketStatusHistoryItem(BaseModel):
    status: TicketStatus
    changed_at: str
    reason: str | None = None


class TicketFieldItem(BaseModel):
    field_name: str
    field_value: str
    is_required: bool
    source: TicketFieldSource
    created_at: str


class TicketStepItem(BaseModel):
    step_order: int
    step_id: str
    output_text: str
    created_at: str


class TicketEventItem(BaseModel):
    event_type: str
    agent_name: str | None = None
    payload_json: str
    created_at: str


class TicketListItem(BaseModel):
    ticket_id: str
    conversation_id: str | None = None
    external_ticket_id: str | None = None
    use_case_id: str
    use_case_display_name: str | None = None
    status: TicketStatus
    language: str
    created_at: str
    updated_at: str
    resolved_at: str | None = None


class TicketDetail(TicketListItem):
    ticket_context: str
    error_message: str | None = None
    status_history: list[TicketStatusHistoryItem] = Field(default_factory=list)
    fields: list[TicketFieldItem] = Field(default_factory=list)
    steps: list[TicketStepItem] = Field(default_factory=list)
    events: list[TicketEventItem] = Field(default_factory=list)


class TicketListResponse(BaseModel):
    items: list[TicketListItem]


class TicketDetailResponse(BaseModel):
    ticket: TicketDetail


class ApproveTicketRequest(BaseModel):
    reviewed_by: str
    note: str | None = None

    @field_validator("reviewed_by")
    @classmethod
    def validate_reviewed_by(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reviewed_by must not be empty")
        return normalized

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RejectTicketRequest(BaseModel):
    reviewed_by: str
    reason: str

    @field_validator("reviewed_by", "reason")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field must not be empty")
        return normalized


class ValidationErrorResponse(BaseModel):
    validation_errors: list[str]
