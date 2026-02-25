from __future__ import annotations

import importlib
import json
import sys
from typing import Any

from fastapi.testclient import TestClient


def _load_backend_module(tmp_path, monkeypatch):
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("HELP_DESK_DB_PATH", str(db_path))

    if "backend" in sys.modules:
        del sys.modules["backend"]
    backend_module = importlib.import_module("backend")
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

    publish_v1 = client.post(f"/api/admin/categories/{category_id}/publish", json={})
    assert publish_v1.status_code == 200

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

    publish_v2 = client.post(f"/api/admin/categories/{category_id}/publish", json={})
    assert publish_v2.status_code == 200
    published_version = publish_v2.json()["category"]["published_version_number"]

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
    response = client.post("/api/chat", json={"message": "Unknown request, please help"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"]
    assert isinstance(payload["events"], list)
    assert payload["events"][0]["kind"] == "info"
    assert "Skipping" in payload["events"][0]["text"]


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
    response = client.post("/api/chat", json={"message": "Necesito ayuda con acceso"})

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
    response = client.post("/api/chat/stream", json={"message": "hi"})

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

    first_chat = client.post("/api/chat", json={"message": "initial ticket"})
    assert first_chat.status_code == 200
    conversation_id = first_chat.json()["conversation_id"]
    first_snapshot_id = backend_module.CONVERSATIONS[conversation_id].snapshot_id

    create_category_response = client.post(
        "/api/admin/categories",
        json=_category_payload(display_name="Snapshot Refresh Category"),
    )
    assert create_category_response.status_code == 200
    category_id = create_category_response.json()["category"]["category_id"]

    publish_response = client.post(f"/api/admin/categories/{category_id}/publish", json={})
    assert publish_response.status_code == 200
    current_snapshot_id = backend_module.RUNTIME_SNAPSHOT.snapshot_id
    assert current_snapshot_id != first_snapshot_id

    second_chat = client.post(
        "/api/chat",
        json={"message": "follow-up ticket", "conversation_id": conversation_id},
    )
    assert second_chat.status_code == 200
    state = backend_module.CONVERSATIONS[conversation_id]
    assert state.snapshot_id == current_snapshot_id
    assert seen_agents[-1] is backend_module.RUNTIME_SNAPSHOT.triage_agent


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
        iter(backend_module.RUNTIME_SNAPSHOT.specialists_by_use_case_id.values())
    )
    conversation_id = "specialist-stale"
    backend_module.CONVERSATIONS[conversation_id] = backend_module.ConversationState(
        snapshot_id="outdated-snapshot",
        current_agent=specialist_agent,
    )

    response = client.post(
        "/api/chat",
        json={"message": "continue specialist flow", "conversation_id": conversation_id},
    )
    assert response.status_code == 200
    state = backend_module.CONVERSATIONS[conversation_id]
    assert state.snapshot_id == "outdated-snapshot"
    assert seen_agents[-1] is specialist_agent


def test_category_archive_and_restore_updates_runtime_handoffs(tmp_path, monkeypatch) -> None:
    backend_module = _load_backend_module(tmp_path, monkeypatch)
    client = TestClient(backend_module.app)

    base_handoff_count = len(backend_module.RUNTIME_SNAPSHOT.triage_agent.handoffs)
    create_response = client.post(
        "/api/admin/categories",
        json=_category_payload(display_name="Runtime Count Category"),
    )
    assert create_response.status_code == 200
    category_id = create_response.json()["category"]["category_id"]

    publish_response = client.post(f"/api/admin/categories/{category_id}/publish", json={})
    assert publish_response.status_code == 200
    after_publish = len(backend_module.RUNTIME_SNAPSHOT.triage_agent.handoffs)
    assert after_publish == base_handoff_count + 1

    archive_response = client.post(f"/api/admin/categories/{category_id}/archive", json={})
    assert archive_response.status_code == 200
    after_archive = len(backend_module.RUNTIME_SNAPSHOT.triage_agent.handoffs)
    assert after_archive == base_handoff_count

    restore_response = client.post(f"/api/admin/categories/{category_id}/restore", json={})
    assert restore_response.status_code == 200
    after_restore = len(backend_module.RUNTIME_SNAPSHOT.triage_agent.handoffs)
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
