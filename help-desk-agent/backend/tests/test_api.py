from __future__ import annotations

import importlib
import json
import sys
from typing import Any

from fastapi.testclient import TestClient


def _clear_backend_modules() -> None:
    module_names = [
        name for name in sys.modules if name == "backend" or name.startswith("backend.")
    ]
    for name in module_names:
        del sys.modules[name]


def _load_backend_module(tmp_path, monkeypatch):
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("HELP_DESK_DB_PATH", str(db_path))
    _clear_backend_modules()
    backend_module = importlib.import_module("backend.api.main")
    return importlib.reload(backend_module)


def _category_payload(display_name: str = "Access Ops") -> dict[str, Any]:
    return {
        "definition": {
            "display_name": display_name,
            "description": "Category for access related tasks.",
            "allowed_step_ids": [
                "verify_requester",
                "reset_ecrew_access",
                "append_resolution_note",
                "manual_instruction",
            ],
            "default_handoff_description": "Handles account recovery.",
            "default_routing_description": "Route access reset requests here.",
            "default_required_fields": ["ticket_id", "requester_name"],
            "default_steps": [
                {"step_id": "verify_requester", "params": {}},
                {"step_id": "reset_ecrew_access", "params": {}},
            ],
        }
    }


def _use_case_payload(
    category_id: str,
    display_name: str = "Reset Account",
) -> dict[str, Any]:
    return {
        "category_id": category_id,
        "slug": "api-created-case",
        "definition": {
            "display_name": display_name,
            "handoff_description": "API handoff description.",
            "routing_description": "API routing description for access reset tickets.",
            "required_fields": ["ticket_id", "requester_name"],
            "steps": [
                {"step_id": "verify_requester", "params": {}},
                {"step_id": "reset_ecrew_access", "params": {}},
            ],
        },
    }


def test_admin_steps_endpoint(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    response = client.get("/api/admin/steps")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert any(item["step_id"] == "manual_instruction" for item in payload["items"])


def test_health_endpoint(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_reseed_defaults_requires_confirm_token(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    response = client.post(
        "/api/admin/bootstrap/reseed-defaults",
        json={"confirm_token": "WRONG_TOKEN"},
    )
    assert response.status_code == 422


def test_admin_reseed_defaults_resets_and_recreates_seed_catalog(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    create_category_response = client.post(
        "/api/admin/categories",
        json=_category_payload(display_name="Transient Category"),
    )
    assert create_category_response.status_code == 200
    category_id = create_category_response.json()["category"]["category_id"]
    assert client.post(f"/api/admin/categories/{category_id}/publish", json={}).status_code == 200

    create_use_case_response = client.post(
        "/api/admin/use-cases",
        json={
            **_use_case_payload(category_id, display_name="Transient use case"),
            "slug": "transient-use-case",
        },
    )
    assert create_use_case_response.status_code == 200
    use_case_id = create_use_case_response.json()["use_case"]["use_case_id"]
    assert client.post(f"/api/admin/use-cases/{use_case_id}/publish", json={}).status_code == 200

    published_items = backend_module.USE_CASE_REPOSITORY.list_published_use_cases()
    backend_module.TICKET_REPOSITORY.start_workflow_execution(
        conversation_id="reseed-test-conversation",
        use_case_id=published_items[0].use_case_id,
        language="en",
        ticket_context="Need help with USDV-999999",
        external_ticket_id="USDV-999999",
        agent_name="Reseed Test Agent",
    )

    categories_before = backend_module.CATEGORY_REPOSITORY.list_categories(include_archived=True)
    use_cases_before = backend_module.USE_CASE_REPOSITORY.list_use_cases(include_archived=True)
    tickets_before = backend_module.TICKET_REPOSITORY.list_tickets(limit=200, offset=0)

    response = client.post(
        "/api/admin/bootstrap/reseed-defaults",
        json={"confirm_token": "RESET_DEFAULTS"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["deleted_counts"] == {
        "tickets": len(tickets_before),
        "use_cases": len(use_cases_before),
        "categories": len(categories_before),
    }
    assert payload["seeded_counts"] == {
        "categories": 2,
        "use_cases": 4,
    }

    categories_after = backend_module.CATEGORY_REPOSITORY.list_categories(include_archived=True)
    assert sorted(item.slug for item in categories_after) == [
        "access-reset",
        "employee-onboarding",
    ]

    use_cases_after = backend_module.USE_CASE_REPOSITORY.list_use_cases(include_archived=True)
    assert len(use_cases_after) == 4
    slugs_after = {item.slug for item in use_cases_after}
    assert "reset-acceso-ecrew" in slugs_after
    assert "alta-email-efos-pelesys" in slugs_after

    published_after = {
        item.slug: item for item in backend_module.USE_CASE_REPOSITORY.list_published_use_cases()
    }
    assert published_after["reset-acceso-ecrew"].definition.required_fields == [
        "ticket_id",
        "requester_name",
        "requester_id",
        "affected_platforms",
    ]
    assert published_after["alta-email-efos-pelesys"].definition.required_fields == [
        "ticket_id",
        "requester_name",
        "employee_name",
        "employee_batch",
        "target_systems",
    ]


def test_system_default_use_case_endpoints_are_blocked(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    list_response = client.get("/api/admin/use-cases?include_archived=true")
    assert list_response.status_code == 200
    default_item = next(
        item for item in list_response.json()["items"] if item["is_system_default"] is True
    )
    use_case_id = default_item["use_case_id"]

    detail_response = client.get(f"/api/admin/use-cases/{use_case_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()["use_case"]
    definition = detail["draft_definition"] or detail["published_definition"]
    assert definition is not None
    definition_payload = {
        key: value for key, value in definition.items() if key != "version_number"
    }

    update_response = client.put(
        f"/api/admin/use-cases/{use_case_id}/draft",
        json={
            "category_id": detail["category_id"],
            "definition": definition_payload,
        },
    )
    publish_response = client.post(f"/api/admin/use-cases/{use_case_id}/publish", json={})
    archive_response = client.post(f"/api/admin/use-cases/{use_case_id}/archive", json={})
    restore_response = client.post(f"/api/admin/use-cases/{use_case_id}/restore", json={})
    migrate_response = client.post(
        f"/api/admin/use-cases/{use_case_id}/migrate-category-version",
        json={
            "category_id": detail["category_id"],
            "category_version_number": detail["category_version_number"],
        },
    )

    for response in [
        update_response,
        publish_response,
        archive_response,
        restore_response,
        migrate_response,
    ]:
        assert response.status_code == 409
        assert "System default use-cases" in response.text


def test_v2_use_case_list_accepts_boolean_include_archived(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    create_category_response = client.post(
        "/api/admin/categories",
        json=_category_payload(display_name="Archived List Category"),
    )
    assert create_category_response.status_code == 200
    category_id = create_category_response.json()["category"]["category_id"]
    assert client.post(f"/api/admin/categories/{category_id}/publish", json={}).status_code == 200

    create_use_case_response = client.post(
        "/api/admin/use-cases",
        json=_use_case_payload(category_id),
    )
    assert create_use_case_response.status_code == 200
    use_case_id = create_use_case_response.json()["use_case"]["use_case_id"]
    assert client.post(f"/api/admin/use-cases/{use_case_id}/archive", json={}).status_code == 200

    excluded = client.get("/api/admin/use-cases?include_archived=false")
    included = client.get("/api/admin/use-cases?include_archived=true")

    assert excluded.status_code == 200
    assert included.status_code == 200
    excluded_ids = {item["use_case_id"] for item in excluded.json()["items"]}
    included_ids = {item["use_case_id"] for item in included.json()["items"]}
    assert use_case_id not in excluded_ids
    assert use_case_id in included_ids


def test_category_crud_flow(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    create_response = client.post("/api/admin/categories", json=_category_payload())
    assert create_response.status_code == 200
    category_id = create_response.json()["category"]["category_id"]

    publish_response = client.post(f"/api/admin/categories/{category_id}/publish", json={})
    assert publish_response.status_code == 200
    use_cases_response = client.get("/api/admin/use-cases")
    assert use_cases_response.status_code == 200
    use_cases = use_cases_response.json()["items"]
    assert any(
        item["category_id"] == category_id and item["is_system_default"] is True
        for item in use_cases
    )

    archive_response = client.post(f"/api/admin/categories/{category_id}/archive", json={})
    assert archive_response.status_code == 200
    assert archive_response.json()["archived"] is True

    restore_response = client.post(f"/api/admin/categories/{category_id}/restore", json={})
    assert restore_response.status_code == 200
    assert restore_response.json()["archived"] is False


def test_create_publish_archive_restore_use_case(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    create_category_response = client.post(
        "/api/admin/categories",
        json=_category_payload(display_name="UseCaseCategory"),
    )
    assert create_category_response.status_code == 200
    category_id = create_category_response.json()["category"]["category_id"]

    publish_category_response = client.post(
        f"/api/admin/categories/{category_id}/publish",
        json={},
    )
    assert publish_category_response.status_code == 200

    create_use_case_response = client.post(
        "/api/admin/use-cases",
        json=_use_case_payload(category_id),
    )
    assert create_use_case_response.status_code == 200
    use_case_id = create_use_case_response.json()["use_case"]["use_case_id"]

    publish_use_case_response = client.post(
        f"/api/admin/use-cases/{use_case_id}/publish",
        json={},
    )
    assert publish_use_case_response.status_code == 200

    archive_use_case_response = client.post(
        f"/api/admin/use-cases/{use_case_id}/archive",
        json={},
    )
    assert archive_use_case_response.status_code == 200
    assert archive_use_case_response.json()["archived"] is True

    restore_use_case_response = client.post(
        f"/api/admin/use-cases/{use_case_id}/restore",
        json={},
    )
    assert restore_use_case_response.status_code == 200
    assert restore_use_case_response.json()["archived"] is False


def test_publish_category_and_migrate_use_case(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    create_category_response = client.post(
        "/api/admin/categories",
        json=_category_payload(display_name="MigrationCategory"),
    )
    assert create_category_response.status_code == 200
    category = create_category_response.json()["category"]
    category_id = category["category_id"]

    publish_response = client.post(f"/api/admin/categories/{category_id}/publish", json={})
    assert publish_response.status_code == 200

    create_use_case_response = client.post(
        "/api/admin/use-cases",
        json={
            **_use_case_payload(category_id, display_name="Migration case"),
            "slug": "migration-case",
        },
    )
    assert create_use_case_response.status_code == 200
    use_case_id = create_use_case_response.json()["use_case"]["use_case_id"]

    publish_use_case = client.post(f"/api/admin/use-cases/{use_case_id}/publish", json={})
    assert publish_use_case.status_code == 200

    update_category_response = client.put(
        f"/api/admin/categories/{category_id}/draft",
        json={
            "definition": {
                **_category_payload(display_name="MigrationCategory")["definition"],
                "allowed_step_ids": [
                    "verify_requester",
                    "reset_ecrew_access",
                    "append_resolution_note",
                    "manual_instruction",
                ],
            }
        },
    )
    assert update_category_response.status_code == 200

    publish_updated_category = client.post(f"/api/admin/categories/{category_id}/publish", json={})
    assert publish_updated_category.status_code == 200
    published_version = publish_updated_category.json()["category"]["published_version_number"]

    migrate_response = client.post(
        f"/api/admin/use-cases/{use_case_id}/migrate-category-version",
        json={
            "category_id": category_id,
            "category_version_number": published_version,
        },
    )
    assert migrate_response.status_code == 200
    migrated_payload = migrate_response.json()["use_case"]
    assert migrated_payload["category_id"] == category_id
    assert migrated_payload["category_version_number"] == published_version


def test_chat_endpoint_with_stubbed_runner(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)

    class UnknownRunItem:
        def __init__(self, agent):
            self.agent = agent

    class FakeRunResult:
        def __init__(self, agent, input_items):
            self.new_items = [UnknownRunItem(agent)]
            self.last_agent = agent
            self._input_items = input_items

        def to_input_list(self):
            return self._input_items

    async def fake_run(agent, input_items):
        return FakeRunResult(agent, input_items)

    monkeypatch.setattr(backend_module.Runner, "run", fake_run)

    client = TestClient(backend_module.app)
    response = client.post(
        "/api/user/assistant/chat", json={"message": "Unknown request, please help"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"]
    assert isinstance(payload["events"], list)
    assert payload["events"][0]["kind"] == "info"
    assert "Skipping" in payload["events"][0]["text"]


def test_legacy_user_assistant_chat_alias_still_works(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)

    class UnknownRunItem:
        def __init__(self, agent):
            self.agent = agent

    class FakeRunResult:
        def __init__(self, agent, input_items):
            self.new_items = [UnknownRunItem(agent)]
            self.last_agent = agent
            self._input_items = input_items

        def to_input_list(self):
            return self._input_items

    async def fake_run(agent, input_items):
        return FakeRunResult(agent, input_items)

    monkeypatch.setattr(backend_module.Runner, "run", fake_run)

    client = TestClient(backend_module.app)
    response = client.post("/api/chat", json={"message": "Unknown request, please help"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"]
    assert isinstance(payload["events"], list)


def test_chat_endpoint_localizes_backend_events_in_spanish(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)

    class UnknownRunItem:
        def __init__(self, agent):
            self.agent = agent

    class FakeRunResult:
        def __init__(self, agent, input_items):
            self.new_items = [UnknownRunItem(agent)]
            self.last_agent = agent
            self._input_items = input_items

        def to_input_list(self):
            return self._input_items

    async def fake_run(agent, input_items):
        return FakeRunResult(agent, input_items)

    monkeypatch.setattr(backend_module.Runner, "run", fake_run)

    client = TestClient(backend_module.app)
    response = client.post(
        "/api/user/assistant/chat", json={"message": "Necesito ayuda con acceso"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["events"][0]["kind"] == "info"
    assert "Omitiendo" in payload["events"][0]["text"]


def test_chat_stream_endpoint_with_stubbed_runner(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)

    class UnknownRunItem:
        def __init__(self, agent):
            self.agent = agent

    class FakeStreamResult:
        def __init__(self, agent, input_items):
            self.last_agent = agent
            self._input_items = input_items

        async def stream_events(self):
            raw_data = type(
                "RawData",
                (),
                {"type": "response.output_text.delta", "delta": "Hola"},
            )()
            raw_event = type(
                "RawEvent",
                (),
                {"type": "raw_response_event", "data": raw_data},
            )()
            run_item_event = type(
                "RunItemEvent",
                (),
                {
                    "type": "run_item_stream_event",
                    "item": UnknownRunItem(self.last_agent),
                },
            )()
            yield raw_event
            yield run_item_event

        def to_input_list(self):
            return self._input_items

    def fake_run_streamed(agent, input_items):
        return FakeStreamResult(agent, input_items)

    monkeypatch.setattr(backend_module.Runner, "run_streamed", fake_run_streamed)

    client = TestClient(backend_module.app)
    response = client.post("/api/user/assistant/chat/stream", json={"message": "hi"})

    assert response.status_code == 200
    lines = [line for line in response.text.splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines]
    payload_types = [payload["type"] for payload in payloads]

    assert payloads[0]["type"] == "start"
    assert payloads[1]["type"] == "text_delta"
    assert payloads[1]["delta"] == "Hola"
    assert "event" in payload_types
    assert payloads[-1]["type"] == "final"
    assert payloads[-1]["conversation_id"]


def test_legacy_user_assistant_chat_stream_alias_still_works(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)

    class UnknownRunItem:
        def __init__(self, agent):
            self.agent = agent

    class FakeStreamResult:
        def __init__(self, agent, input_items):
            self.last_agent = agent
            self._input_items = input_items

        async def stream_events(self):
            raw_data = type(
                "RawData",
                (),
                {"type": "response.output_text.delta", "delta": "Hola"},
            )()
            raw_event = type(
                "RawEvent",
                (),
                {"type": "raw_response_event", "data": raw_data},
            )()
            yield raw_event

        def to_input_list(self):
            return self._input_items

    def fake_run_streamed(agent, input_items):
        return FakeStreamResult(agent, input_items)

    monkeypatch.setattr(backend_module.Runner, "run_streamed", fake_run_streamed)

    client = TestClient(backend_module.app)
    response = client.post("/api/chat/stream", json={"message": "hi"})

    assert response.status_code == 200
    lines = [line for line in response.text.splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines]
    assert payloads[0]["type"] == "start"
    assert payloads[-1]["type"] == "final"


def test_legacy_user_assistant_reset_alias_still_works(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)

    class FakeRunResult:
        def __init__(self, agent, input_items):
            self.new_items = []
            self.last_agent = agent
            self._input_items = input_items

        def to_input_list(self):
            return self._input_items

    async def fake_run(agent, input_items):
        return FakeRunResult(agent, input_items)

    monkeypatch.setattr(backend_module.Runner, "run", fake_run)

    client = TestClient(backend_module.app)
    chat_response = client.post(
        "/api/user/assistant/chat",
        json={"message": "please help with access"},
    )
    assert chat_response.status_code == 200
    conversation_id = chat_response.json()["conversation_id"]

    reset_response = client.post("/api/reset", json={"conversation_id": conversation_id})
    assert reset_response.status_code == 200
    assert reset_response.json() == {"deleted": True}


def test_chat_rebinds_stale_triage_conversation_snapshot(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    seen_agents = []

    class FakeRunResult:
        def __init__(self, agent, input_items):
            self.new_items = []
            self.last_agent = agent
            self._input_items = input_items

        def to_input_list(self):
            return self._input_items

    async def fake_run(agent, input_items):
        seen_agents.append(agent)
        return FakeRunResult(agent, input_items)

    monkeypatch.setattr(backend_module.Runner, "run", fake_run)
    client = TestClient(backend_module.app)

    first_chat = client.post("/api/user/assistant/chat", json={"message": "initial ticket"})
    assert first_chat.status_code == 200
    conversation_id = first_chat.json()["conversation_id"]
    first_snapshot_id = backend_module.USER_ASSISTANT_CONVERSATIONS[conversation_id].snapshot_id

    create_category_response = client.post(
        "/api/admin/categories",
        json=_category_payload(display_name="Snapshot Refresh Category"),
    )
    assert create_category_response.status_code == 200
    category_id = create_category_response.json()["category"]["category_id"]

    publish_response = client.post(f"/api/admin/categories/{category_id}/publish", json={})
    assert publish_response.status_code == 200
    current_snapshot_id = backend_module.USER_ASSISTANT_RUNTIME_SNAPSHOT.snapshot_id
    assert current_snapshot_id != first_snapshot_id

    second_chat = client.post(
        "/api/user/assistant/chat",
        json={"message": "follow-up ticket", "conversation_id": conversation_id},
    )
    assert second_chat.status_code == 200
    state = backend_module.USER_ASSISTANT_CONVERSATIONS[conversation_id]
    assert state.snapshot_id == current_snapshot_id
    assert seen_agents[-1] is backend_module.USER_ASSISTANT_RUNTIME_SNAPSHOT.triage_agent


def test_chat_keeps_specialist_on_stale_snapshot(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    seen_agents = []

    class FakeRunResult:
        def __init__(self, agent, input_items):
            self.new_items = []
            self.last_agent = agent
            self._input_items = input_items

        def to_input_list(self):
            return self._input_items

    async def fake_run(agent, input_items):
        seen_agents.append(agent)
        return FakeRunResult(agent, input_items)

    monkeypatch.setattr(backend_module.Runner, "run", fake_run)
    client = TestClient(backend_module.app)

    specialist_agent = next(
        iter(backend_module.USER_ASSISTANT_RUNTIME_SNAPSHOT.specialists_by_use_case_id.values())
    )
    conversation_id = "specialist-stale"
    backend_module.USER_ASSISTANT_CONVERSATIONS[conversation_id] = backend_module.ConversationState(
        snapshot_id="outdated-snapshot",
        current_agent=specialist_agent,
    )

    response = client.post(
        "/api/user/assistant/chat",
        json={"message": "continue specialist flow", "conversation_id": conversation_id},
    )
    assert response.status_code == 200
    state = backend_module.USER_ASSISTANT_CONVERSATIONS[conversation_id]
    assert state.snapshot_id == "outdated-snapshot"
    assert seen_agents[-1] is specialist_agent


def test_category_archive_and_restore_updates_runtime_handoffs(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    base_handoff_count = len(backend_module.USER_ASSISTANT_RUNTIME_SNAPSHOT.triage_agent.handoffs)
    create_response = client.post(
        "/api/admin/categories",
        json=_category_payload(display_name="Runtime Count Category"),
    )
    assert create_response.status_code == 200
    category_id = create_response.json()["category"]["category_id"]

    publish_response = client.post(f"/api/admin/categories/{category_id}/publish", json={})
    assert publish_response.status_code == 200
    after_publish = len(backend_module.USER_ASSISTANT_RUNTIME_SNAPSHOT.triage_agent.handoffs)
    assert after_publish == base_handoff_count + 1

    archive_response = client.post(f"/api/admin/categories/{category_id}/archive", json={})
    assert archive_response.status_code == 200
    after_archive = len(backend_module.USER_ASSISTANT_RUNTIME_SNAPSHOT.triage_agent.handoffs)
    assert after_archive == base_handoff_count

    restore_response = client.post(f"/api/admin/categories/{category_id}/restore", json={})
    assert restore_response.status_code == 200
    after_restore = len(backend_module.USER_ASSISTANT_RUNTIME_SNAPSHOT.triage_agent.handoffs)
    assert after_restore == base_handoff_count + 1


def test_admin_assistant_chat_endpoint(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)

    class UnknownRunItem:
        def __init__(self, agent):
            self.agent = agent

    class FakeRunResult:
        def __init__(self, agent, input_items):
            self.new_items = [UnknownRunItem(agent)]
            self.last_agent = agent
            self._input_items = input_items

        def to_input_list(self):
            return self._input_items

    async def fake_run(agent, input_items):
        return FakeRunResult(agent, input_items)

    monkeypatch.setattr(backend_module.Runner, "run", fake_run)

    client = TestClient(backend_module.app)
    response = client.post(
        "/api/admin/assistant/chat",
        json={"message": "Ayudame a crear una categoria para nomina."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"]
    assert isinstance(payload["events"], list)
    assert payload["events"][0]["kind"] == "info"
    assert "Omitiendo" in payload["events"][0]["text"]


def _seed_ticket_record(backend_module, external_ticket_id: str = "USDV-176285") -> str:
    from backend.domain.models import TicketFieldSource
    from backend.storage.ticket_repository import (
        TicketEventWrite,
        TicketFieldWrite,
        TicketStepWrite,
    )

    use_case = backend_module.USE_CASE_REPOSITORY.list_use_cases(include_archived=False)[0]
    ticket_id = backend_module.TICKET_REPOSITORY.start_workflow_execution(
        conversation_id="api-ticket-conversation",
        use_case_id=use_case.use_case_id,
        language="en",
        ticket_context=f"Ticket context for {external_ticket_id}",
        external_ticket_id=external_ticket_id,
        agent_name="API Test Specialist",
    )
    backend_module.TICKET_REPOSITORY.complete_workflow_execution_success(
        ticket_id=ticket_id,
        fields=[
            TicketFieldWrite(
                field_name="ticket_id",
                field_value=external_ticket_id,
                is_required=True,
                source=TicketFieldSource.PROVIDED,
            )
        ],
        steps=[
            TicketStepWrite(
                step_order=1,
                step_id="verify_requester",
                output_text="Requester verified.",
            )
        ],
        events=[
            TicketEventWrite(
                event_type="workflow_completed",
                agent_name="API Test Specialist",
                payload_json='{"result":"ok"}',
            )
        ],
    )
    return str(ticket_id)


def test_admin_ticket_endpoints_list_and_detail(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    ticket_id = _seed_ticket_record(backend_module, external_ticket_id="USDV-176999")

    client = TestClient(backend_module.app)
    list_response = client.get("/api/admin/tickets")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert any(item["ticket_id"] == ticket_id for item in list_payload["items"])

    filtered_response = client.get("/api/admin/tickets?status=pending_review")
    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert any(item["ticket_id"] == ticket_id for item in filtered_payload["items"])

    detail_response = client.get(f"/api/admin/tickets/{ticket_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["ticket"]
    assert detail_payload["ticket_id"] == ticket_id
    assert detail_payload["status"] == "pending_review"
    assert detail_payload["fields"][0]["field_name"] == "ticket_id"
    assert detail_payload["steps"][0]["step_id"] == "verify_requester"


def test_admin_ticket_detail_returns_404_for_unknown_ticket(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    response = client.get("/api/admin/tickets/unknown-ticket-id")
    assert response.status_code == 404


def test_admin_ticket_approve_and_reject_endpoints(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    approve_ticket_id = _seed_ticket_record(backend_module, external_ticket_id="USDV-177001")
    approve_response = client.post(
        f"/api/admin/tickets/{approve_ticket_id}/approve",
        json={"reviewed_by": "Jane Doe", "note": "Looks good."},
    )
    assert approve_response.status_code == 200
    approve_payload = approve_response.json()["ticket"]
    assert approve_payload["status"] == "approved"
    assert any(item["event_type"] == "ticket_approved" for item in approve_payload["events"])
    approved_list = client.get("/api/admin/tickets?status=approved")
    assert approved_list.status_code == 200
    assert any(item["ticket_id"] == approve_ticket_id for item in approved_list.json()["items"])

    reject_ticket_id = _seed_ticket_record(backend_module, external_ticket_id="USDV-177002")
    reject_response = client.post(
        f"/api/admin/tickets/{reject_ticket_id}/reject",
        json={
            "reviewed_by": "Jane Doe",
            "reason": "Requester identity does not match.",
        },
    )
    assert reject_response.status_code == 200
    reject_payload = reject_response.json()["ticket"]
    assert reject_payload["status"] == "rejected"
    assert reject_payload["error_message"] == "Requester identity does not match."
    assert any(item["event_type"] == "ticket_rejected" for item in reject_payload["events"])
    rejected_list = client.get("/api/admin/tickets?status=rejected")
    assert rejected_list.status_code == 200
    assert any(item["ticket_id"] == reject_ticket_id for item in rejected_list.json()["items"])


def test_admin_ticket_review_endpoints_validate_input_and_transitions(
    tmp_path, monkeypatch
) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)
    ticket_id = _seed_ticket_record(backend_module, external_ticket_id="USDV-177003")

    missing_reviewer_response = client.post(
        f"/api/admin/tickets/{ticket_id}/approve",
        json={"reviewed_by": " ", "note": "bad"},
    )
    assert missing_reviewer_response.status_code == 422

    missing_reason_response = client.post(
        f"/api/admin/tickets/{ticket_id}/reject",
        json={"reviewed_by": "Jane Doe", "reason": " "},
    )
    assert missing_reason_response.status_code == 422

    first_approve = client.post(
        f"/api/admin/tickets/{ticket_id}/approve",
        json={"reviewed_by": "Jane Doe"},
    )
    assert first_approve.status_code == 200

    second_approve = client.post(
        f"/api/admin/tickets/{ticket_id}/approve",
        json={"reviewed_by": "Jane Doe"},
    )
    assert second_approve.status_code == 409
