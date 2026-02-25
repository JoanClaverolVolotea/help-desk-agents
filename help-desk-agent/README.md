# Help Desk Agent Platform

This project is a non-technical help desk platform with:

- User ticket portal for quick guided ticket creation.
- Category + use-case CRUD (draft/publish/archive/restore).
- Deterministic workflow execution after triage.
- Separate **Tech Assistant** chat for IT operations support.

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
- `frontend/`: Vite + React app with role-based routes (`/`, `/user`, `/it/...`).

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

## Frontend route map

- `/`: role landing page (choose User Portal vs IT Console).
- `/user`: end-user ticket portal (guided form + chat transcript).
- `/it/admin/categories`: IT category operations.
- `/it/admin/tickets`: IT ticket registry (read-only list and detail).
- `/it/admin/use-cases`: IT use-case operations.
- `/it/assistant`: IT technical assistant chat.

Backend APIs remain under `/api/*` only.

Optional CLI runner:

```bash
uv run --env-file backend/.env python -m backend.cli.main
```

## User workflow

1. Open `/user`.
2. Describe the issue in free text and send it in chat format.
3. Continue the same conversation or reset to open a new one.

## IT workflow

1. Open `/it/admin/categories` or `/it/admin/use-cases`.
2. Manage **Categorias**:
   - Create/edit drafts.
   - Publish versions.
   - Archive/restore categories.
   - Optionally reseed defaults (destructive reset) from case-aligned templates.
3. Manage **Casos de uso**:
   - Create/edit drafts linked to a published category.
   - Publish versions.
   - Archive/restore use cases.
4. After publishing a category, optionally migrate linked use cases to the new category version.
5. Open `/it/assistant` for tech-team guidance in a separate session.
6. Open `/it/admin/tickets` to inspect workflow-executed tickets, extracted fields, and execution timeline.

## API summary

API endpoints:

- `GET /api/health`
- `POST /api/chat`
- `POST /api/chat/stream`
- `POST /api/reset`
- `POST /api/admin/assistant/chat`
- `POST /api/admin/assistant/reset`
- `POST /api/admin/bootstrap/reseed-defaults`
- `GET /api/admin/steps`
- `GET /api/admin/categories?include_archived=true|false`
- `GET /api/admin/categories/{category_id}`
- `POST /api/admin/categories`
- `PUT /api/admin/categories/{category_id}/draft`
- `POST /api/admin/categories/{category_id}/publish`
- `POST /api/admin/categories/{category_id}/archive`
- `POST /api/admin/categories/{category_id}/restore`
- `GET /api/admin/use-cases?include_archived=true|false`
- `GET /api/admin/use-cases/{use_case_id}`
- `POST /api/admin/use-cases`
- `PUT /api/admin/use-cases/{use_case_id}/draft`
- `POST /api/admin/use-cases/{use_case_id}/publish`
- `POST /api/admin/use-cases/{use_case_id}/archive`
- `POST /api/admin/use-cases/{use_case_id}/restore`
- `POST /api/admin/use-cases/{use_case_id}/migrate-category-version`
- `GET /api/admin/tickets`
- `GET /api/admin/tickets/{ticket_id}`

## Validation commands

Run from `help-desk-agent/`:

```bash
uv run ruff check backend
uv run mypy backend
uv run pytest backend/tests -q
cd frontend && npm run build
```
