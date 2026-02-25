from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import backend.api.deps as deps
from backend.api.schemas.admin import (
    ArchiveRestoreResponse,
    CategoryDetailResponse,
    CategoryListResponse,
    CreateCategoryRequest,
    StepCatalogResponse,
    UpdateCategoryDraftRequest,
)
from backend.api_internal.runtime_sync import (
    archive_category_and_sync,
    publish_category_and_sync,
    restore_category_and_sync,
)
from backend.api_internal.validation import slugify
from backend.domain.templates import (
    list_step_catalog,
    to_category_draft_definition,
    validate_category_definition,
)
from backend.storage import CategoryNotFoundError, NoDraftAvailableError

router = APIRouter()


@router.get("/api/v2/admin/steps", response_model=StepCatalogResponse)
async def admin_steps() -> StepCatalogResponse:
    return StepCatalogResponse(items=list_step_catalog())


@router.get("/api/v2/admin/categories", response_model=CategoryListResponse)
async def admin_list_categories_v2(
    include_archived: bool = Query(default=False),
) -> CategoryListResponse:
    return CategoryListResponse(
        items=deps.CATEGORY_REPOSITORY.list_categories(include_archived=include_archived)
    )


@router.get("/api/v2/admin/categories/{category_id}", response_model=CategoryDetailResponse)
async def admin_get_category(category_id: str) -> CategoryDetailResponse:
    try:
        category = deps.CATEGORY_REPOSITORY.get_category_detail(category_id, include_archived=True)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CategoryDetailResponse(category=category)


@router.post("/api/v2/admin/categories", response_model=CategoryDetailResponse)
async def admin_create_category(request: CreateCategoryRequest) -> CategoryDetailResponse:
    validation_errors = validate_category_definition(request.definition)
    if validation_errors:
        raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

    category_slug = slugify(request.slug or request.definition.display_name)
    draft_definition = to_category_draft_definition(request.definition)

    try:
        detail = deps.CATEGORY_REPOSITORY.create_category_with_draft(
            category_slug, draft_definition
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return CategoryDetailResponse(category=detail)


@router.put("/api/v2/admin/categories/{category_id}/draft", response_model=CategoryDetailResponse)
async def admin_update_category_draft(
    category_id: str,
    request: UpdateCategoryDraftRequest,
) -> CategoryDetailResponse:
    validation_errors = validate_category_definition(request.definition)
    if validation_errors:
        raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

    draft_definition = to_category_draft_definition(request.definition)

    try:
        detail = deps.CATEGORY_REPOSITORY.update_draft(category_id, draft_definition)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CategoryDetailResponse(category=detail)


@router.post(
    "/api/v2/admin/categories/{category_id}/publish", response_model=CategoryDetailResponse
)
async def admin_publish_category(category_id: str) -> CategoryDetailResponse:
    try:
        detail = await publish_category_and_sync(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoDraftAvailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return CategoryDetailResponse(category=detail)


@router.post(
    "/api/v2/admin/categories/{category_id}/archive", response_model=ArchiveRestoreResponse
)
async def admin_archive_category(category_id: str) -> ArchiveRestoreResponse:
    try:
        await archive_category_and_sync(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ArchiveRestoreResponse(success=True, entity_id=category_id, archived=True)


@router.post(
    "/api/v2/admin/categories/{category_id}/restore", response_model=ArchiveRestoreResponse
)
async def admin_restore_category(category_id: str) -> ArchiveRestoreResponse:
    try:
        await restore_category_and_sync(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ArchiveRestoreResponse(success=True, entity_id=category_id, archived=False)
