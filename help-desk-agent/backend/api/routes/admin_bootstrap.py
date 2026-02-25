from __future__ import annotations

from fastapi import APIRouter

from backend.api.schemas.admin import ReseedDefaultsRequest, ReseedDefaultsResponse
from backend.api_internal.runtime_sync import reseed_defaults_and_refresh_runtime

router = APIRouter()


@router.post(
    "/api/admin/bootstrap/reseed-defaults",
    response_model=ReseedDefaultsResponse,
)
async def admin_reseed_defaults(
    request: ReseedDefaultsRequest,
) -> ReseedDefaultsResponse:
    del request
    return await reseed_defaults_and_refresh_runtime()
