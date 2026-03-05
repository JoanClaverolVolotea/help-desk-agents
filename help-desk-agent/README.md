# Help Desk Agent Platform

Help Desk Agent is an MVP workspace inside this repository.

Its current goal is to design, test, and iterate on a practical help-desk automation agent built with the OpenAI Agents SDK while staying aligned with upstream SDK patterns and releases.

In practice, this project focuses on:

- User-facing guided ticket intake
- IT-facing console for routing policies and runbooks
- Deterministic runbook execution for repeatable outcomes
- Ticket registry and event history for auditability and traceability

## Repository goal and scope

This folder exists to improve agent quality over time without turning into a broad monorepo refactor effort.

- Primary objective: produce a production-minded Help Desk Agent MVP that is easy to run, inspect, and evolve.
- Learning objective: apply current OpenAI Agents SDK best practices and keep this MVP synced with upstream behavior changes.
- Scope boundary: only files under `help-desk-agent/` are in scope for implementation changes.
- Non-goal: changing core SDK internals outside this folder.

If upstream SDK behavior, setup steps, or APIs change, update this folder's docs and implementation notes so contributors can keep working from accurate guidance.

## Architecture

- `backend/`: FastAPI API + runtime + SQLite repositories
- `frontend/`: React/Vite UI for user and IT operations
- `data/`: local SQLite database (`helpdesk.db`)
- `docs/`: schema and case references

Detailed component docs:

- Backend guide: [`backend/README.md`](backend/README.md)
- Frontend guide: [`frontend/README.md`](frontend/README.md)
- Contributor rules for this folder: [`AGENTS.md`](AGENTS.md)
- DB schema: [`docs/db/schema.md`](docs/db/schema.md)
- Case references: [`docs/cases/README.md`](docs/cases/README.md)

## How the MVP works

1. A requester starts a ticket through the guided chat UI.
2. The backend triages the request and selects a routing policy.
3. A deterministic runbook executes with required fields and guardrails.
4. The system records every key step in the ticket registry.
5. The ticket enters IT review, where reviewers approve or reject.

This keeps outcomes consistent for common requests while preserving human review for final control.

## Prerequisites

- Python 3.10+
- `uv`
- Node.js + npm
- OpenAI API key in `backend/.env`

## Upstream and SDK sync

Keep this MVP aligned with the official OpenAI Agents SDK sources:

- Canonical upstream repository: `https://github.com/openai/openai-agents-python`
- Canonical package source: `https://pypi.org/project/openai-agents/`
- Sync cadence: before new feature work and at least weekly

Preferred dependency update commands:

```bash
uv add --upgrade openai-agents
# or
pip install -U openai-agents
```

After updating, verify local behavior and update docs under `help-desk-agent/` when upstream behavior, setup, or APIs changed.

## Quick start

From `help-desk-agent/`:

> Backend commands can run directly from this directory.
> The backend package bootstraps the repository `src/` path automatically so local `agents` imports resolve.

1. Configure backend env:

```bash
echo 'OPENAI_API_KEY=sk-...' > backend/.env
```

2. Start backend:

```bash
uv run --env-file backend/.env -m backend.api.main
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
