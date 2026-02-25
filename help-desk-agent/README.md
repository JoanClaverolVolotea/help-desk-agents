# Help Desk Agent Platform

This project is a non-technical help desk platform with:

- Operator chat for live ticket handling.
- Category + use-case CRUD (draft/publish/archive/restore).
- Deterministic workflow execution after triage.
- Separate **Tech Assistant** chat with handoff agents to help create categories.

## Project layout

- `backend/backend.py`: FastAPI app (chat, admin, tech assistant APIs).
- `backend/main.py`: Optional terminal chat runner.
- `backend/db.py`: SQLite schema + migration-safe initialization.
- `backend/repository.py`: Category/use-case repositories.
- `backend/templates.py`: Step catalog, validators, and seed data.
- `backend/agent_runtime/`: Runtime wiring split by goal (bootstrap, snapshot, triage, specialists).
- `backend/workflows/`: Deterministic use-case step execution and tool bindings.
- `frontend/`: Vite + React app with `Chat`, `Admin`, and `Tech Assistant` tabs.

## Requirements

- `.env` with `OPENAI_API_KEY=...`
- Node.js + npm

## Quick start

From repository root:

1. Create `.env`:

```bash
echo 'OPENAI_API_KEY=sk-...' > .env
```

2. Start backend API:

```bash
uv run --env-file .env python help-desk-agent/backend/backend.py
```

3. Start frontend in another terminal:

```bash
cd help-desk-agent/frontend
npm install
npm run dev
```

4. Open `http://127.0.0.1:5173`.

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

Stable chat APIs:

- `GET /api/health`
- `POST /api/chat`
- `POST /api/reset`

Tech assistant APIs:

- `POST /api/admin/assistant/chat`
- `POST /api/admin/assistant/reset`

Admin catalog APIs:

- `GET /api/admin/steps`
- `GET /api/admin/categories`
- `GET /api/admin/categories/{category_id}`
- `POST /api/admin/categories`
- `PUT /api/admin/categories/{category_id}/draft`
- `POST /api/admin/categories/{category_id}/publish`
- `POST /api/admin/categories/{category_id}/archive`
- `POST /api/admin/categories/{category_id}/restore`

Admin use-case APIs:

- `GET /api/admin/use-cases?include_archived=0|1`
- `GET /api/admin/use-cases/{use_case_id}`
- `POST /api/admin/use-cases`
- `PUT /api/admin/use-cases/{use_case_id}/draft`
- `POST /api/admin/use-cases/{use_case_id}/publish`
- `POST /api/admin/use-cases/{use_case_id}/archive`
- `POST /api/admin/use-cases/{use_case_id}/restore`
- `POST /api/admin/use-cases/{use_case_id}/migrate-category-version`

## Validation commands

```bash
uv run ruff check help-desk-agent/backend
uv run mypy help-desk-agent/backend
uv run pytest help-desk-agent/backend/tests -q
cd help-desk-agent/frontend && npm run build
```
