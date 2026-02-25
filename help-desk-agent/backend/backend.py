from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from collections.abc import AsyncIterator
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from import_paths import configure_backend_import_paths
from pydantic import BaseModel

configure_backend_import_paths(__file__)

from agent_runtime.bootstrap import (  # noqa: E402
    build_snapshot_from_repository,
    initialize_repositories,
)
from language_policy import (  # noqa: E402
    detect_user_language,
    normalize_language,
    translate_backend_text,
)
from models import (  # noqa: E402
    ArchiveRestoreResponse,
    CategoryDefinitionInput,
    CategoryDetail,
    CategoryDetailResponse,
    CategoryListResponse,
    CreateCategoryRequest,
    CreateUseCaseRequest,
    CreateUseCaseResponse,
    MigrateCategoryVersionRequest,
    PublishUseCaseResponse,
    StepCatalogResponse,
    UpdateCategoryDraftRequest,
    UpdateUseCaseDraftRequest,
    UseCaseDefinitionInput,
    UseCaseDetail,
    UseCaseDetailResponse,
    UseCaseListResponse,
    UseCaseStep,
)
from repository import (  # noqa: E402
    CategoryNotFoundError,
    CategoryRepository,
    NoDraftAvailableError,
    UseCaseNotFoundError,
    UseCaseRepository,
)
from templates import (  # noqa: E402
    list_step_catalog,
    to_category_draft_definition,
    to_use_case_draft_definition,
    validate_category_definition,
    validate_use_case_definition,
)

from agents import (  # noqa: E402
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX  # noqa: E402


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatEvent(BaseModel):
    kind: str
    agent: str
    text: str


class ChatResponse(BaseModel):
    conversation_id: str
    current_agent: str
    events: list[ChatEvent]


class ResetRequest(BaseModel):
    conversation_id: str


class ResetResponse(BaseModel):
    deleted: bool


@dataclass
class ConversationState:
    snapshot_id: str
    current_agent: Agent[Any]
    response_language: str = "en"
    input_items: list[TResponseInputItem] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


CATEGORY_REPOSITORY = CategoryRepository()
USE_CASE_REPOSITORY = UseCaseRepository()
initialize_repositories(CATEGORY_REPOSITORY, USE_CASE_REPOSITORY)

RUNTIME_SNAPSHOT = build_snapshot_from_repository(USE_CASE_REPOSITORY)
RUNTIME_LOCK = asyncio.Lock()


def _build_admin_assistant_triage_agent() -> Agent[Any]:
    @function_tool(
        name_override="list_categories",
        description_override="List current categories and status.",
    )
    def list_categories_tool(include_archived: bool = False) -> str:
        language = _current_response_language()
        categories = CATEGORY_REPOSITORY.list_categories(include_archived=include_archived)
        if not categories:
            return translate_backend_text("no_categories_available", language)
        lines = []
        for category in categories:
            lines.append(
                translate_backend_text(
                    "category_status_line",
                    language,
                    category_id=category.category_id,
                    display_name=category.display_name,
                    published_version=category.published_version_number,
                    draft_version=category.draft_version_number,
                    archived=category.archived,
                )
            )
        return "\n".join(lines)

    @function_tool(
        name_override="list_step_catalog",
        description_override="Show all safe step IDs that categories can use.",
    )
    def list_step_catalog_tool() -> str:
        language = _current_response_language()
        lines: list[str] = []
        for item in list_step_catalog():
            key = f"step_{item.step_id}"
            try:
                description = translate_backend_text(key, language)
            except KeyError:
                description = item.description
            lines.append(f"- {item.step_id}: {description}")
        return "\n".join(lines)

    @function_tool(
        name_override="create_category_draft",
        description_override=(
            "Create a category draft. Pass comma-separated step IDs and required fields."
        ),
    )
    def create_category_draft_tool(
        display_name: str,
        description: str,
        allowed_step_ids_csv: str,
        default_handoff_description: str,
        default_routing_description: str,
        default_required_fields_csv: str = "",
        default_step_ids_csv: str = "",
    ) -> str:
        language = _current_response_language()
        allowed_steps = _parse_csv_list(allowed_step_ids_csv)
        default_required_fields = _parse_csv_list(default_required_fields_csv)
        default_step_ids = _parse_csv_list(default_step_ids_csv) or allowed_steps[:1]

        definition = {
            "display_name": display_name,
            "description": description,
            "allowed_step_ids": allowed_steps,
            "default_handoff_description": default_handoff_description,
            "default_routing_description": default_routing_description,
            "default_required_fields": default_required_fields,
            "default_steps": [
                UseCaseStep(step_id=step_id, params={}).model_dump() for step_id in default_step_ids
            ],
        }

        definition_input = CategoryDefinitionInput.model_validate(definition)
        errors = validate_category_definition(definition_input)
        if errors:
            return translate_backend_text(
                "validation_errors_prefix",
                language,
                errors="; ".join(errors),
            )
        definition_model = to_category_draft_definition(definition_input)

        slug = _slugify(display_name)
        try:
            detail = CATEGORY_REPOSITORY.create_category_with_draft(slug, definition_model)
        except ValueError as exc:
            return str(exc)

        return translate_backend_text(
            "category_draft_created",
            language,
            category_id=detail.category_id,
            slug=detail.slug,
            draft_version=detail.draft_version_number,
        )

    @function_tool(
        name_override="publish_category_draft",
        description_override="Publish an existing category draft by category_id.",
    )
    async def publish_category_draft_tool(category_id: str) -> str:
        language = _current_response_language()
        try:
            detail = await _publish_category_and_sync(category_id)
        except (CategoryNotFoundError, NoDraftAvailableError) as exc:
            return str(exc)
        return translate_backend_text(
            "category_published",
            language,
            category_id=detail.category_id,
            version=detail.published_version_number,
        )

    creator_agent = Agent(
        name="Category Creator Specialist",
        handoff_description="Helps tech team create and publish new categories.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You help the technical team create category drafts.

Workflow:
1. Clarify the intended use of the category.
2. Call list_step_catalog and propose safe steps.
3. Call create_category_draft when enough info is available.
4. Ask whether to publish; call publish_category_draft only with explicit confirmation.
5. Reply only in the language of the user's latest message.
6. Do not include translations or bilingual sections.
""",
        tools=[
            list_categories_tool,
            list_step_catalog_tool,
            create_category_draft_tool,
            publish_category_draft_tool,
        ],
    )

    lifecycle_agent = Agent(
        name="Category Lifecycle Specialist",
        handoff_description="Helps with category updates, archive, and restore guidance.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You help the technical team inspect and maintain category lifecycle.

Always start by calling list_categories and then explain what to do next.
If the user asks to create a new category, handoff to Category Creator Specialist.
Reply only in the language of the user's latest message.
Do not include translations or bilingual sections.
""",
        tools=[list_categories_tool],
    )

    triage_agent = Agent(
        name="Tech Team Assistant Triage",
        handoff_description="Routes technical admin requests to the right specialist.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You triage technical admin requests.

- Handoff to Category Creator Specialist for creating/publishing new categories.
- Handoff to Category Lifecycle Specialist for inspection/maintenance.
- Ask clarifying questions when intent is ambiguous.
- Reply only in the language of the user's latest message.
- Do not include translations or bilingual sections.
""",
        handoffs=[creator_agent, lifecycle_agent],
    )

    creator_agent.handoffs.append(triage_agent)
    lifecycle_agent.handoffs.append(triage_agent)
    return triage_agent


ADMIN_ASSISTANT_TRIAGE_AGENT = _build_admin_assistant_triage_agent()

app = FastAPI(title="Help Desk Agent API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONVERSATIONS: dict[str, ConversationState] = {}
ADMIN_ASSISTANT_CONVERSATIONS: dict[str, ConversationState] = {}
RESPONSE_LANGUAGE_CONTEXT: ContextVar[str] = ContextVar(
    "help_desk_response_language",
    default="en",
)


def _current_response_language() -> str:
    return normalize_language(RESPONSE_LANGUAGE_CONTEXT.get())


def _serialize_tool_output(output: Any) -> str:
    if isinstance(output, str):
        return output
    try:
        return json.dumps(output, ensure_ascii=True)
    except TypeError:
        return str(output)


def _event_from_item(item: Any, language: str) -> ChatEvent | None:
    agent_name = item.agent.name
    if isinstance(item, MessageOutputItem):
        text = ItemHelpers.text_message_output(item)
        if not text:
            return None
        return ChatEvent(kind="message", agent=agent_name, text=text)
    if isinstance(item, HandoffOutputItem):
        return ChatEvent(
            kind="handoff",
            agent=agent_name,
            text=translate_backend_text(
                "handoff_event",
                language,
                source=item.source_agent.name,
                target=item.target_agent.name,
            ),
        )
    if isinstance(item, ToolCallItem):
        tool_name = getattr(item.raw_item, "name", item.__class__.__name__)
        return ChatEvent(
            kind="tool_call",
            agent=agent_name,
            text=translate_backend_text("tool_call_event", language, tool_name=tool_name),
        )
    if isinstance(item, ToolCallOutputItem):
        return ChatEvent(
            kind="tool_output",
            agent=agent_name,
            text=_serialize_tool_output(item.output),
        )
    return ChatEvent(
        kind="info",
        agent=agent_name,
        text=translate_backend_text(
            "skip_event",
            language,
            item_class=item.__class__.__name__,
        ),
    )


def _ndjson_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True) + "\n"


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    return normalized or uuid.uuid4().hex[:12]


def _parse_csv_list(raw_value: str) -> list[str]:
    return [token.strip() for token in raw_value.split(",") if token.strip()]


def _is_triage_agent(agent: Agent[Any]) -> bool:
    return agent.name == "Help Desk Triage Agent"


async def _publish_category_and_sync(category_id: str) -> CategoryDetail:
    detail = CATEGORY_REPOSITORY.publish_draft(category_id)
    if detail.published_definition is not None:
        USE_CASE_REPOSITORY.create_or_update_default_use_case_for_category(detail)
    await _refresh_runtime_snapshot()
    return detail


async def _archive_category_and_sync(category_id: str) -> None:
    CATEGORY_REPOSITORY.archive_category(category_id)
    USE_CASE_REPOSITORY.archive_default_use_case_for_category(category_id)
    await _refresh_runtime_snapshot()


async def _restore_category_and_sync(category_id: str) -> None:
    detail = CATEGORY_REPOSITORY.restore_category(category_id)
    if detail.published_definition is not None:
        USE_CASE_REPOSITORY.create_or_update_default_use_case_for_category(detail)
    await _refresh_runtime_snapshot()


async def _refresh_runtime_snapshot() -> None:
    async with RUNTIME_LOCK:
        global RUNTIME_SNAPSHOT
        RUNTIME_SNAPSHOT = build_snapshot_from_repository(USE_CASE_REPOSITORY)


def _validate_use_case_payload(
    category_id: str,
    definition_input: UseCaseDefinitionInput,
) -> tuple[list[str], int]:
    category_definition = CATEGORY_REPOSITORY.get_published_category_definition(category_id)
    validation_errors = validate_use_case_definition(
        definition_input,
        allowed_step_ids=set(category_definition.allowed_step_ids),
    )
    return validation_errors, category_definition.version_number


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    conversation_id = request.conversation_id or uuid.uuid4().hex[:16]
    state = CONVERSATIONS.get(conversation_id)
    if state is None:
        state = ConversationState(
            snapshot_id=RUNTIME_SNAPSHOT.snapshot_id,
            current_agent=RUNTIME_SNAPSHOT.triage_agent,
        )
        CONVERSATIONS[conversation_id] = state

    async with state.lock:
        if state.snapshot_id != RUNTIME_SNAPSHOT.snapshot_id and _is_triage_agent(
            state.current_agent
        ):
            state.current_agent = RUNTIME_SNAPSHOT.triage_agent
            state.snapshot_id = RUNTIME_SNAPSHOT.snapshot_id

        state.response_language = detect_user_language(message, state.response_language)
        state.input_items.append({"content": message, "role": "user"})
        context_token = RESPONSE_LANGUAGE_CONTEXT.set(state.response_language)
        try:
            with trace("Help desk web chat", group_id=conversation_id):
                result = await Runner.run(state.current_agent, state.input_items)
        finally:
            RESPONSE_LANGUAGE_CONTEXT.reset(context_token)

        events: list[ChatEvent] = []
        for item in result.new_items:
            event = _event_from_item(item, state.response_language)
            if event is not None:
                events.append(event)

        state.input_items = result.to_input_list()
        state.current_agent = result.last_agent

        return ChatResponse(
            conversation_id=conversation_id,
            current_agent=state.current_agent.name,
            events=events,
        )


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    conversation_id = request.conversation_id or uuid.uuid4().hex[:16]
    state = CONVERSATIONS.get(conversation_id)
    if state is None:
        state = ConversationState(
            snapshot_id=RUNTIME_SNAPSHOT.snapshot_id,
            current_agent=RUNTIME_SNAPSHOT.triage_agent,
        )
        CONVERSATIONS[conversation_id] = state

    async def stream_events() -> AsyncIterator[str]:
        async with state.lock:
            if state.snapshot_id != RUNTIME_SNAPSHOT.snapshot_id and _is_triage_agent(
                state.current_agent
            ):
                state.current_agent = RUNTIME_SNAPSHOT.triage_agent
                state.snapshot_id = RUNTIME_SNAPSHOT.snapshot_id

            state.response_language = detect_user_language(message, state.response_language)
            state.input_items.append({"content": message, "role": "user"})
            yield _ndjson_line(
                {
                    "type": "start",
                    "conversation_id": conversation_id,
                    "current_agent": state.current_agent.name,
                }
            )

            context_token = RESPONSE_LANGUAGE_CONTEXT.set(state.response_language)
            try:
                with trace("Help desk web chat streamed", group_id=conversation_id):
                    streamed_result = Runner.run_streamed(state.current_agent, state.input_items)
                    try:
                        async for stream_event in streamed_result.stream_events():
                            if stream_event.type == "agent_updated_stream_event":
                                yield _ndjson_line(
                                    {
                                        "type": "agent_updated",
                                        "agent": stream_event.new_agent.name,
                                    }
                                )
                                continue

                            if stream_event.type == "raw_response_event":
                                raw_event = stream_event.data
                                if getattr(raw_event, "type", "") == "response.output_text.delta":
                                    delta = getattr(raw_event, "delta", "")
                                    if delta:
                                        yield _ndjson_line(
                                            {
                                                "type": "text_delta",
                                                "delta": delta,
                                            }
                                        )
                                continue

                            if stream_event.type == "run_item_stream_event":
                                run_event = _event_from_item(
                                    stream_event.item,
                                    state.response_language,
                                )
                                if run_event is None:
                                    continue
                                yield _ndjson_line(
                                    {
                                        "type": "event",
                                        "event": run_event.model_dump(),
                                    }
                                )
                    except Exception as exc:
                        yield _ndjson_line({"type": "error", "detail": str(exc)})
                        return
            finally:
                RESPONSE_LANGUAGE_CONTEXT.reset(context_token)

            state.input_items = streamed_result.to_input_list()
            state.current_agent = streamed_result.last_agent
            yield _ndjson_line(
                {
                    "type": "final",
                    "conversation_id": conversation_id,
                    "current_agent": state.current_agent.name,
                }
            )

    return StreamingResponse(stream_events(), media_type="application/x-ndjson")


@app.post("/api/reset", response_model=ResetResponse)
async def reset_conversation(request: ResetRequest) -> ResetResponse:
    deleted = CONVERSATIONS.pop(request.conversation_id, None) is not None
    return ResetResponse(deleted=deleted)


@app.post("/api/admin/assistant/chat", response_model=ChatResponse)
async def admin_assistant_chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    conversation_id = request.conversation_id or uuid.uuid4().hex[:16]
    state = ADMIN_ASSISTANT_CONVERSATIONS.get(conversation_id)
    if state is None:
        state = ConversationState(
            snapshot_id="admin-assistant",
            current_agent=ADMIN_ASSISTANT_TRIAGE_AGENT,
        )
        ADMIN_ASSISTANT_CONVERSATIONS[conversation_id] = state

    async with state.lock:
        state.response_language = detect_user_language(message, state.response_language)
        state.input_items.append({"content": message, "role": "user"})
        context_token = RESPONSE_LANGUAGE_CONTEXT.set(state.response_language)
        try:
            with trace("Help desk admin assistant chat", group_id=conversation_id):
                result = await Runner.run(state.current_agent, state.input_items)
        finally:
            RESPONSE_LANGUAGE_CONTEXT.reset(context_token)

        events: list[ChatEvent] = []
        for item in result.new_items:
            event = _event_from_item(item, state.response_language)
            if event is not None:
                events.append(event)

        state.input_items = result.to_input_list()
        state.current_agent = result.last_agent

        return ChatResponse(
            conversation_id=conversation_id,
            current_agent=state.current_agent.name,
            events=events,
        )


@app.post("/api/admin/assistant/reset", response_model=ResetResponse)
async def admin_assistant_reset_conversation(request: ResetRequest) -> ResetResponse:
    deleted = ADMIN_ASSISTANT_CONVERSATIONS.pop(request.conversation_id, None) is not None
    return ResetResponse(deleted=deleted)


@app.get("/api/admin/steps", response_model=StepCatalogResponse)
async def admin_steps() -> StepCatalogResponse:
    return StepCatalogResponse(items=list_step_catalog())


@app.get("/api/admin/categories", response_model=CategoryListResponse)
async def admin_list_categories(
    include_archived: int = Query(default=0, ge=0, le=1),
) -> CategoryListResponse:
    return CategoryListResponse(
        items=CATEGORY_REPOSITORY.list_categories(include_archived=bool(include_archived))
    )


@app.get("/api/admin/categories/{category_id}", response_model=CategoryDetailResponse)
async def admin_get_category(category_id: str) -> CategoryDetailResponse:
    try:
        category = CATEGORY_REPOSITORY.get_category_detail(category_id, include_archived=True)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CategoryDetailResponse(category=category)


@app.post("/api/admin/categories", response_model=CategoryDetailResponse)
async def admin_create_category(request: CreateCategoryRequest) -> CategoryDetailResponse:
    validation_errors = validate_category_definition(request.definition)
    if validation_errors:
        raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

    slug = _slugify(request.slug or request.definition.display_name)
    draft_definition = to_category_draft_definition(request.definition)

    try:
        detail = CATEGORY_REPOSITORY.create_category_with_draft(slug, draft_definition)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return CategoryDetailResponse(category=detail)


@app.put("/api/admin/categories/{category_id}/draft", response_model=CategoryDetailResponse)
async def admin_update_category_draft(
    category_id: str,
    request: UpdateCategoryDraftRequest,
) -> CategoryDetailResponse:
    validation_errors = validate_category_definition(request.definition)
    if validation_errors:
        raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

    draft_definition = to_category_draft_definition(request.definition)

    try:
        detail = CATEGORY_REPOSITORY.update_draft(category_id, draft_definition)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CategoryDetailResponse(category=detail)


@app.post("/api/admin/categories/{category_id}/publish", response_model=CategoryDetailResponse)
async def admin_publish_category(category_id: str) -> CategoryDetailResponse:
    try:
        detail = await _publish_category_and_sync(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoDraftAvailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return CategoryDetailResponse(category=detail)


@app.post("/api/admin/categories/{category_id}/archive", response_model=ArchiveRestoreResponse)
async def admin_archive_category(category_id: str) -> ArchiveRestoreResponse:
    try:
        await _archive_category_and_sync(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ArchiveRestoreResponse(success=True, entity_id=category_id, archived=True)


@app.post("/api/admin/categories/{category_id}/restore", response_model=ArchiveRestoreResponse)
async def admin_restore_category(category_id: str) -> ArchiveRestoreResponse:
    try:
        await _restore_category_and_sync(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ArchiveRestoreResponse(success=True, entity_id=category_id, archived=False)


@app.get("/api/admin/use-cases", response_model=UseCaseListResponse)
async def admin_list_use_cases(
    include_archived: int = Query(default=0, ge=0, le=1),
) -> UseCaseListResponse:
    return UseCaseListResponse(
        items=USE_CASE_REPOSITORY.list_use_cases(include_archived=bool(include_archived))
    )


@app.get("/api/admin/use-cases/{use_case_id}", response_model=UseCaseDetailResponse)
async def admin_get_use_case(use_case_id: str) -> UseCaseDetailResponse:
    try:
        detail = USE_CASE_REPOSITORY.get_use_case_detail(use_case_id, include_archived=True)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return UseCaseDetailResponse(use_case=detail)


@app.post("/api/admin/use-cases", response_model=CreateUseCaseResponse)
async def admin_create_use_case(request: CreateUseCaseRequest) -> CreateUseCaseResponse:
    try:
        validation_errors, category_version_number = _validate_use_case_payload(
            request.category_id,
            request.definition,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if validation_errors:
        raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

    slug = _slugify(request.slug or request.definition.display_name)
    draft_definition = to_use_case_draft_definition(request.definition)

    try:
        detail = USE_CASE_REPOSITORY.create_use_case_with_draft(
            slug=slug,
            category_id=request.category_id,
            category_version_number=category_version_number,
            draft_definition=draft_definition,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return CreateUseCaseResponse(use_case=detail)


@app.put("/api/admin/use-cases/{use_case_id}/draft", response_model=UseCaseDetailResponse)
async def admin_update_use_case_draft(
    use_case_id: str,
    request: UpdateUseCaseDraftRequest,
) -> UseCaseDetailResponse:
    try:
        USE_CASE_REPOSITORY.get_use_case_detail(use_case_id, include_archived=True)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        validation_errors, category_version_number = _validate_use_case_payload(
            request.category_id,
            request.definition,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if validation_errors:
        raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

    draft_definition = to_use_case_draft_definition(request.definition)

    detail = USE_CASE_REPOSITORY.update_draft(
        use_case_id=use_case_id,
        category_id=request.category_id,
        category_version_number=category_version_number,
        draft_definition=draft_definition,
    )
    return UseCaseDetailResponse(use_case=detail)


@app.post("/api/admin/use-cases/{use_case_id}/publish", response_model=PublishUseCaseResponse)
async def admin_publish_use_case(use_case_id: str) -> PublishUseCaseResponse:
    try:
        detail: UseCaseDetail = USE_CASE_REPOSITORY.publish_draft(use_case_id)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoDraftAvailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await _refresh_runtime_snapshot()
    return PublishUseCaseResponse(use_case=detail)


@app.post("/api/admin/use-cases/{use_case_id}/archive", response_model=ArchiveRestoreResponse)
async def admin_archive_use_case(use_case_id: str) -> ArchiveRestoreResponse:
    try:
        USE_CASE_REPOSITORY.archive_use_case(use_case_id)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    await _refresh_runtime_snapshot()
    return ArchiveRestoreResponse(success=True, entity_id=use_case_id, archived=True)


@app.post("/api/admin/use-cases/{use_case_id}/restore", response_model=ArchiveRestoreResponse)
async def admin_restore_use_case(use_case_id: str) -> ArchiveRestoreResponse:
    try:
        USE_CASE_REPOSITORY.restore_use_case(use_case_id)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    await _refresh_runtime_snapshot()
    return ArchiveRestoreResponse(success=True, entity_id=use_case_id, archived=False)


@app.post(
    "/api/admin/use-cases/{use_case_id}/migrate-category-version",
    response_model=UseCaseDetailResponse,
)
async def admin_migrate_use_case_category_version(
    use_case_id: str,
    request: MigrateCategoryVersionRequest,
) -> UseCaseDetailResponse:
    try:
        detail = USE_CASE_REPOSITORY.get_use_case_detail(use_case_id, include_archived=True)
    except UseCaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        category_definition = CATEGORY_REPOSITORY.get_published_category_definition(
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

    migrated = USE_CASE_REPOSITORY.migrate_category_version(
        use_case_id=use_case_id,
        category_id=request.category_id,
        category_version_number=request.category_version_number,
    )
    return UseCaseDetailResponse(use_case=migrated)


if __name__ == "__main__":
    host = os.getenv("HELP_DESK_API_HOST", "127.0.0.1")
    port = int(os.getenv("HELP_DESK_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
