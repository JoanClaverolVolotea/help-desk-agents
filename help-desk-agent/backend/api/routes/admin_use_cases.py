from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import backend.api.deps as deps
from backend.api.schemas.admin import (
    ArchiveRestoreResponse,
    CreateUseCaseRequest,
    CreateUseCaseResponse,
    MigrateCategoryVersionRequest,
    PublishUseCaseResponse,
    UpdateUseCaseDraftRequest,
    UseCaseDefinitionInput,
    UseCaseDetailResponse,
    UseCaseListResponse,
)
from backend.api_internal.runtime_sync import refresh_runtime_snapshot
from backend.api_internal.validation import slugify, validate_use_case_payload
from backend.domain.templates import (
    to_use_case_draft_definition,
    validate_use_case_definition,
)
from backend.storage import (
    CategoryNotFoundError,
    NoDraftAvailableError,
    UseCaseNotFoundError,
)

router = APIRouter()


@router.get("/api/v2/admin/use-cases", response_model=UseCaseListResponse)
async def admin_list_use_cases_v2(
    include_archived: bool = Query(default=False),
) -> UseCaseListResponse:
    return UseCaseListResponse(
        items=deps.USE_CASE_REPOSITORY.list_use_cases(include_archived=include_archived)
    )


@router.get("/api/v2/admin/use-cases/{use_case_id}", response_model=UseCaseDetailResponse)
async def admin_get_use_case(use_case_id: str) -> UseCaseDetailResponse:
    try:
        detail = deps.USE_CASE_REPOSITORY.get_use_case_detail(use_case_id, include_archived=True)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return UseCaseDetailResponse(use_case=detail)


@router.post("/api/v2/admin/use-cases", response_model=CreateUseCaseResponse)
async def admin_create_use_case(request: CreateUseCaseRequest) -> CreateUseCaseResponse:
    try:
        validation_errors, category_version_number = validate_use_case_payload(
            deps.CATEGORY_REPOSITORY,
            request.category_id,
            request.definition,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if validation_errors:
        raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

    use_case_slug = slugify(request.slug or request.definition.display_name)
    draft_definition = to_use_case_draft_definition(request.definition)

    try:
        detail = deps.USE_CASE_REPOSITORY.create_use_case_with_draft(
            slug=use_case_slug,
            category_id=request.category_id,
            category_version_number=category_version_number,
            draft_definition=draft_definition,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return CreateUseCaseResponse(use_case=detail)


@router.put("/api/v2/admin/use-cases/{use_case_id}/draft", response_model=UseCaseDetailResponse)
async def admin_update_use_case_draft(
    use_case_id: str,
    request: UpdateUseCaseDraftRequest,
) -> UseCaseDetailResponse:
    try:
        deps.USE_CASE_REPOSITORY.get_use_case_detail(use_case_id, include_archived=True)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        validation_errors, category_version_number = validate_use_case_payload(
            deps.CATEGORY_REPOSITORY,
            request.category_id,
            request.definition,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if validation_errors:
        raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

    draft_definition = to_use_case_draft_definition(request.definition)

    detail = deps.USE_CASE_REPOSITORY.update_draft(
        use_case_id=use_case_id,
        category_id=request.category_id,
        category_version_number=category_version_number,
        draft_definition=draft_definition,
    )
    return UseCaseDetailResponse(use_case=detail)


@router.post("/api/v2/admin/use-cases/{use_case_id}/publish", response_model=PublishUseCaseResponse)
async def admin_publish_use_case(use_case_id: str) -> PublishUseCaseResponse:
    try:
        detail = deps.USE_CASE_REPOSITORY.publish_draft(use_case_id)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoDraftAvailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await refresh_runtime_snapshot()
    return PublishUseCaseResponse(use_case=detail)


@router.post("/api/v2/admin/use-cases/{use_case_id}/archive", response_model=ArchiveRestoreResponse)
async def admin_archive_use_case(use_case_id: str) -> ArchiveRestoreResponse:
    try:
        deps.USE_CASE_REPOSITORY.archive_use_case(use_case_id)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    await refresh_runtime_snapshot()
    return ArchiveRestoreResponse(success=True, entity_id=use_case_id, archived=True)


@router.post("/api/v2/admin/use-cases/{use_case_id}/restore", response_model=ArchiveRestoreResponse)
async def admin_restore_use_case(use_case_id: str) -> ArchiveRestoreResponse:
    try:
        deps.USE_CASE_REPOSITORY.restore_use_case(use_case_id)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    await refresh_runtime_snapshot()
    return ArchiveRestoreResponse(success=True, entity_id=use_case_id, archived=False)


@router.post(
    "/api/v2/admin/use-cases/{use_case_id}/migrate-category-version",
    response_model=UseCaseDetailResponse,
)
async def admin_migrate_use_case_category_version(
    use_case_id: str,
    request: MigrateCategoryVersionRequest,
) -> UseCaseDetailResponse:
    try:
        detail = deps.USE_CASE_REPOSITORY.get_use_case_detail(use_case_id, include_archived=True)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        category_definition = deps.CATEGORY_REPOSITORY.get_published_category_definition(
            request.category_id,
            request.category_version_number,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    active_definition = detail.draft_definition or detail.published_definition
    if active_definition is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot migrate use case category version without draft or published definition."
            ),
        )

    validation_errors = validate_use_case_definition(
        UseCaseDefinitionInput.model_validate(active_definition.model_dump()),
        allowed_step_ids=set(category_definition.allowed_step_ids),
    )
    if validation_errors:
        raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

    migrated = deps.USE_CASE_REPOSITORY.migrate_category_version(
        use_case_id=use_case_id,
        category_id=request.category_id,
        category_version_number=request.category_version_number,
    )
    return UseCaseDetailResponse(use_case=migrated)
