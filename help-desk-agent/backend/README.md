# Help Desk Backend

FastAPI backend for the Help Desk Agent PoC.

It provides:

- User assistant chat APIs (`/api/user/assistant/chat`, `/api/user/assistant/chat/stream`, `/api/user/assistant/reset`)
- IT admin assistant chat APIs
- Routing policy/category lifecycle APIs
- Runbook/use-case lifecycle APIs
- Ticket registry APIs
- SQLite persistence and repository bootstrapping

## Directory map

- `api/`: FastAPI app entrypoint and HTTP routes
- `api_internal/`: validation helpers
- `chats/`: assistant contexts (`user_assistant`, `admin_assistant`) and shared chat internals
- `domain/`: models, language policy, seed templates
- `storage/`: SQLite schema and repositories
- `workflows/`: deterministic workflow executor + tool integration
- `tests/`: backend tests
- `cli/`: optional terminal runner

## Requirements

- Python 3.10+
- `uv`
- `OPENAI_API_KEY` in `backend/.env`

Example:

```bash
echo 'OPENAI_API_KEY=sk-...' > backend/.env
```

## Run API

From `help-desk-agent/`:

```bash
uv run --env-file backend/.env python -m backend.api.main
```

Defaults:

- Host: `127.0.0.1`
- Port: `8000`

Optional env vars:

- `HELP_DESK_API_HOST`
- `HELP_DESK_API_PORT`
- `HELP_DESK_DB_PATH` (SQLite file override)

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

## API surface

### User assistant chat

- `GET /api/health`
- `POST /api/user/assistant/chat`
- `POST /api/user/assistant/chat/stream`
- `POST /api/user/assistant/reset`

Deprecated aliases (kept for this release, introduced February 26, 2026):

- `POST /api/chat`
- `POST /api/chat/stream`
- `POST /api/reset`

### Admin assistant chat

- `POST /api/admin/assistant/chat`
- `POST /api/admin/assistant/reset`

### Admin bootstrap

- `POST /api/admin/bootstrap/reseed-defaults`
  - Destructive reset + reseed for categories/use-cases/tickets
  - Requires payload: `{"confirm_token":"RESET_DEFAULTS"}`

### Admin catalog and registry

- `GET /api/admin/steps`
- `GET /api/admin/categories`
- `GET /api/admin/categories/{category_id}`
- `POST /api/admin/categories`
- `PUT /api/admin/categories/{category_id}/draft`
- `POST /api/admin/categories/{category_id}/publish`
- `POST /api/admin/categories/{category_id}/archive`
- `POST /api/admin/categories/{category_id}/restore`
- `GET /api/admin/use-cases`
- `GET /api/admin/use-cases/{use_case_id}`
- `POST /api/admin/use-cases`
- `PUT /api/admin/use-cases/{use_case_id}/draft`
- `POST /api/admin/use-cases/{use_case_id}/publish`
- `POST /api/admin/use-cases/{use_case_id}/archive`
- `POST /api/admin/use-cases/{use_case_id}/restore`
- `POST /api/admin/use-cases/{use_case_id}/migrate-category-version`
- `GET /api/admin/tickets`
- `GET /api/admin/tickets/{ticket_id}`

## Assistant architecture

- `chats/user_assistant/`:
  - `graph/triage.py`: user triage agent ("Help Desk Triage Agent").
  - `graph/specialists.py`: use-case specialist builders and workflow tool wiring.
  - `graph/snapshot.py`: runtime graph snapshot assembly.
  - `bootstrap.py`: repository initialization and reseed helpers.
  - `service.py`: user assistant orchestration and runtime refresh/sync operations.
  - `routes.py`: canonical `/api/user/assistant/*` routes plus temporary legacy aliases.
  - `state.py`: conversation state store for user assistant sessions.
- `chats/admin_assistant/`:
  - `graph/triage.py`: admin triage agent ("Tech Team Assistant Triage").
  - `graph/specialists.py`: admin specialist and tool definitions.
  - `graph/snapshot.py`: admin runtime snapshot assembly.
  - `service.py`: admin assistant chat orchestration.
  - `routes.py`: `/api/admin/assistant/*` routes.
  - `state.py`: conversation state store for admin assistant sessions.
- `chats/shared/`:
  - Shared event serialization, request context channel markers, and base conversation state.

## Data model notes

- Routing policies (`categories`) define allowed/default workflow templates.
- Runbooks (`use_cases`) define executable deterministic steps and required fields.
- Ticket registry captures:
  - ticket status timeline
  - resolved fields and sources
  - executed workflow steps
  - workflow events/errors

Schema reference:

- `help-desk-agent/docs/db/schema.md`

## Development commands

From `help-desk-agent/`:

```bash
uv run ruff check backend
uv run mypy backend
uv run pytest backend/tests -q
```

Optional CLI runner:

```bash
uv run --env-file backend/.env python -m backend.cli.main
```
