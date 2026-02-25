# Help Desk Agent Platform

This project is a non-technical help desk platform with:

- Operator chat for live ticket handling.
- Category + use-case CRUD (draft/publish/archive/restore).
- Deterministic workflow execution after triage.
- Separate **Tech Assistant** chat with handoff agents to help create categories.

## Project layout

- `backend/api/main.py`: FastAPI app factory + module entrypoint.
- `backend/api/routes/`: HTTP routes grouped by feature.
- `backend/api_internal/`: non-route API logic (state, runtime sync, event serialization).
- `backend/runtime/`: runtime wiring split by goal (bootstrap, snapshot, triage, specialists).
- `backend/workflows/`: deterministic use-case step execution and tool bindings.
- `backend/storage/`: SQLite repositories split by entity.
- `backend/domain/`: shared models, templates, and language policy.
- `backend/cli/main.py`: optional terminal chat runner.
- `data/`: SQLite data files at the same level as `backend/`.
- `frontend/`: Vite + React app with `Chat`, `Admin`, and `Tech Assistant` tabs.

## Requirements

- `backend/.env` with `OPENAI_API_KEY=...`
- Python 3.10+
- `uv`
- Node.js + npm

## Quick start

All commands below assume your current directory is `help-desk-agent/`.

1. Enter the project folder:

```bash
cd help-desk-agent
```

2. Create backend-local `.env`:

```bash
echo 'OPENAI_API_KEY=sk-...' > backend/.env
```

3. Start backend API:

```bash
uv run --env-file backend/.env python -m backend.api.main
```

4. Start frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

5. Open `http://127.0.0.1:5173`.

Optional CLI runner:

```bash
uv run --env-file backend/.env python -m backend.cli.main
```

## Admin workflow

1. Open `Admin` tab.
2. Manage **Categorias**:
   - Create/edit drafts.
   - Publish versions.
   - Archive/restore categories.
3. Manage **Casos de uso**:
   - Create/edit drafts linked to a published category.
   - Publish versions.
   - Archive/restore use cases.
4. After publishing a category, optionally migrate linked use cases to the new category version.

## Tech team workflow

1. Open `Tech Assistant` tab.
2. Use a separate conversation session to ask for category creation guidance.
3. The assistant triage agent hands off to a category-creation specialist and can create/publish drafts through tools.

## API summary

Canonical API (v2):

- `GET /api/v2/health`
- `POST /api/v2/chat`
- `POST /api/v2/chat/stream`
- `POST /api/v2/reset`
- `POST /api/v2/admin/assistant/chat`
- `POST /api/v2/admin/assistant/reset`
- `GET /api/v2/admin/steps`
- `GET /api/v2/admin/categories?include_archived=true|false`
- `GET /api/v2/admin/categories/{category_id}`
- `POST /api/v2/admin/categories`
- `PUT /api/v2/admin/categories/{category_id}/draft`
- `POST /api/v2/admin/categories/{category_id}/publish`
- `POST /api/v2/admin/categories/{category_id}/archive`
- `POST /api/v2/admin/categories/{category_id}/restore`
- `GET /api/v2/admin/use-cases?include_archived=true|false`
- `GET /api/v2/admin/use-cases/{use_case_id}`
- `POST /api/v2/admin/use-cases`
- `PUT /api/v2/admin/use-cases/{use_case_id}/draft`
- `POST /api/v2/admin/use-cases/{use_case_id}/publish`
- `POST /api/v2/admin/use-cases/{use_case_id}/archive`
- `POST /api/v2/admin/use-cases/{use_case_id}/restore`
- `POST /api/v2/admin/use-cases/{use_case_id}/migrate-category-version`

## Validation commands

Run from `help-desk-agent/`:

```bash
uv run ruff check backend
uv run mypy backend
uv run pytest backend/tests -q
cd frontend && npm run build
```
