from __future__ import annotations

from enum import Enum

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


class ValidationErrorResponse(BaseModel):
    validation_errors: list[str]
