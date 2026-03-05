# Phase 1 Implementation Plan: JIRA Cloud Integration

Date: 2026-03-05
Scope: Phase 1 from `roadmap-26022026.md` (JIRA integration only)
Constraints: All work remains inside `help-desk-agent/`

## Goal

Move the MVP from deterministic simulated workflow outputs to deterministic workflow execution that calls Jira Cloud REST API v3, while keeping the current local ticket registry and approval lifecycle.

## Baseline

Already implemented:
- Multi-agent runtime (triage + specialists) with OpenAI Agents SDK.
- Deterministic workflow executor and step catalog.
- Local ticket lifecycle (`open -> in_progress -> pending_review -> approved/rejected`).
- Admin IT console and API.
- EN/ES language handling and broad backend tests.

Missing for Phase 1:
- Real JIRA read/create/update/comment/transition/attachment operations.
- Environment-based client wiring.
- Sync behavior between local ticket approvals and JIRA transitions.

## Architecture Decision

Use an adapter pattern:
- `InMemoryJiraClient` for development/testing while JIRA PRE access is pending.
- `HttpJiraClient` for real Jira Cloud REST API v3.

Both implement the same `JiraClient` protocol so switching is config-driven.

Planned backend structure:

```text
backend/
  integrations/
    jira/
      protocol.py
      memory_client.py
      http_client.py
      config.py
```

## Required JIRA Operations

1. Search/read issues (JQL).
2. Create issues.
3. Update issue fields.
4. Add comments.
5. Transition status.
6. Read attachments.

## Milestones

### M1. Protocol and Models

Create `JiraClient` protocol and minimal shared models in `backend/integrations/jira/protocol.py`.

Methods:
- `search_issues`
- `create_issue`
- `update_issue`
- `add_comment`
- `transition_issue`
- `get_attachments`
- `get_issue`

Deliverable: type-safe interface contract, no external calls yet.

### M2. In-Memory Mock Client

Implement `InMemoryJiraClient` in `backend/integrations/jira/memory_client.py`.

Behavior:
- Stores issues in memory.
- Generates keys (for example `MOCK-1`).
- Supports simple project/status/issueType filtering.
- Persists comments/transitions per issue.

Tests: `backend/tests/test_jira_memory_client.py`.

### M3. Config and Dependency Wiring

Create `backend/integrations/jira/config.py` and wire client creation in `backend/api/deps.py`.

Environment variables:
- `JIRA_CLIENT_MODE` (`memory` or `http`)
- `JIRA_BASE_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_PROJECT_KEY` (TBD default placeholder)

Deliverable: runtime can use mock now and switch to HTTP later.

### M4. Replace Simulated Step Actions

Update deterministic step handlers in `backend/workflows/executor.py` to call `JiraClient` operations.

Rules:
- If `jira_client` is unavailable, preserve current simulated behavior as fallback.
- `verify_requester` validates existing issue context.
- Provision/reset steps append deterministic comments and update fields if needed.
- Resolution step appends closure note and triggers status transition.

### M5. Local Ticket Lifecycle and JIRA Sync

On admin review actions:
- Approve: transition JIRA issue to completed state and add approval comment.
- Reject: add rejection comment and transition/reopen according to workflow.

Touch points:
- `backend/api/routes/admin_tickets.py`
- `backend/storage/ticket_repository.py` (only where needed for sync orchestration)
- `backend/workflows/tools.py`

### M6. HTTP Jira Cloud Client

Implement `backend/integrations/jira/http_client.py` using Jira Cloud REST API v3.

Endpoints:
- `POST /rest/api/3/search`
- `POST /rest/api/3/issue`
- `PUT /rest/api/3/issue/{key}`
- `POST /rest/api/3/issue/{key}/comment`
- `POST /rest/api/3/issue/{key}/transitions`
- `GET /rest/api/3/issue/{key}?fields=attachment`

Include:
- Basic auth (email + API token).
- Error mapping (auth/not-found/rate-limit).
- Retry/backoff for 429.

Tests: `backend/tests/test_jira_http_client.py` with mocked transport.

### M7. Admin Assistant JIRA Specialist

Add JIRA tools for IT admins:
- Search tickets.
- Get ticket details.
- Create ticket.
- Update ticket.

Touch points:
- `backend/chats/admin_assistant/graph/jira_tools.py`
- `backend/chats/admin_assistant/graph/specialists.py`
- `backend/chats/admin_assistant/graph/triage.py`

## Implementation Order

Recommended order:

1. M1 Protocol and models.
2. M2 In-memory client.
3. M3 Config and dependency wiring.
4. M4 Replace simulated step actions.
5. M5 Local/JIRA sync on review actions.
6. M7 Admin assistant JIRA specialist.
7. M6 Real HTTP client (last, since PRE access is pending).

## Test Strategy

- Keep existing tests passing while introducing protocol-driven integration.
- Add dedicated tests for memory and HTTP clients.
- Extend workflow tests to validate JIRA method calls in deterministic order.
- Extend admin ticket tests to validate approval/rejection synchronization with JIRA.

## Risks and Mitigation

- Unknown JIRA PRE custom field IDs and transition IDs.
  - Mitigation: include a discovery step in M6 and map IDs in configuration.
- JIRA access pending.
  - Mitigation: ship with `InMemoryJiraClient` first.
- Added latency from external calls.
  - Mitigation: keep deterministic flow, add retries only where necessary, and monitor execution times.

## Immediate Next Step

Start M1 now: add `backend/integrations/jira/protocol.py` and shared models to establish the integration contract before any runtime wiring.
