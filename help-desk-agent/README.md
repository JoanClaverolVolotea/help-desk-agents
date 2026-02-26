# Help Desk Agent Platform

Help Desk Agent is a PoC platform with:

- User-facing guided ticket chat
- IT console for routing policies and runbooks
- Deterministic workflow execution
- Ticket registry for execution traceability

## Architecture

- `backend/`: FastAPI API + runtime + SQLite repositories
- `frontend/`: React/Vite UI for user and IT operations
- `data/`: local SQLite database (`helpdesk.db`)
- `docs/`: schema and case references

Detailed component docs:

- Backend guide: [`backend/README.md`](backend/README.md)
- Frontend guide: [`frontend/README.md`](frontend/README.md)
- DB schema: [`docs/db/schema.md`](docs/db/schema.md)
- Case references: [`docs/cases/README.md`](docs/cases/README.md)

## Prerequisites

- Python 3.10+
- `uv`
- Node.js + npm
- OpenAI API key in `backend/.env`

## Quick start

From `help-desk-agent/`:

1. Configure backend env:

```bash
echo 'OPENAI_API_KEY=sk-...' > backend/.env
```

2. Start backend:

```bash
uv run --env-file backend/.env python -m backend.api.main
```

3. Start frontend (new terminal):

```bash
cd frontend
npm install
npm run dev
```

4. Open:

- `http://127.0.0.1:5173`

## Concept model (for business demo)

- **Routing Policy (Category)**: defines domain, allowed steps, and default template.
- **Runbook (Use case)**: executable deterministic workflow with required fields.
- **Ticket Registry**: stores field extraction, workflow steps, status history, and events.

Flow:

1. Ticket intake
2. Routing policy selected by triage
3. Runbook executed by specialist
4. Ticket moved to IT review queue (`pending_review`)
5. IT reviewer approves or rejects the ticket

## Operational notes

- Backend API base URL: `http://127.0.0.1:8000`
- Frontend default URL: `http://127.0.0.1:5173`
- Destructive reseed endpoint:
  - `POST /api/admin/bootstrap/reseed-defaults`
  - Payload: `{"confirm_token":"RESET_DEFAULTS"}`
- Ticket review endpoints:
  - `POST /api/admin/tickets/{ticket_id}/approve`
  - Payload: `{"reviewed_by":"Jane Doe","note":"Looks correct"}`
  - `POST /api/admin/tickets/{ticket_id}/reject`
  - Payload: `{"reviewed_by":"Jane Doe","reason":"Requester ID mismatch"}`

## Validation

From `help-desk-agent/`:

```bash
uv run ruff check backend
uv run mypy backend
uv run pytest backend/tests -q
cd frontend && npm run build
```
