# Help Desk Backend

Backend reference rendered as Mermaid diagrams.

## System map

```mermaid
flowchart TB
    subgraph Inputs["External inputs"]
        UI["Frontend UI"]
        CURL["CLI / curl"]
    end

    subgraph API["FastAPI layer (`backend/api`)"]
        MAIN["main.py"]
        ROUTES["routes/* + chats/*/routes.py"]
        DEPS["deps.py (repositories + runtime snapshot)"]
    end

    subgraph ChatRuntime["Assistant runtime (`backend/chats`)"]
        USTATE["user_assistant/state.py"]
        USVC["user_assistant/service.py"]
        USNAP["user_assistant/graph/snapshot.py"]
        UTRIAGE["user_assistant/graph/triage.py"]
        USPEC["user_assistant/graph/specialists.py"]

        ASTATE["admin_assistant/state.py"]
        ASVC["admin_assistant/service.py"]
        ATRIAGE["admin_assistant/graph/triage.py"]
        ASPEC["admin_assistant/graph/specialists.py"]
    end

    subgraph Domain["Domain + workflow"]
        MODELS["domain/models.py"]
        TEMPLATE["domain/templates.py"]
        LANG["domain/language_policy.py"]
        WFLOW["workflows/executor.py + workflows/tools.py"]
    end

    subgraph Storage["SQLite persistence (`backend/storage`)"]
        DB["db.py (schema + migrations)"]
        CAT["CategoryRepository"]
        UCR["UseCaseRepository"]
        TKT["TicketRepository"]
        SQLITE[("data/helpdesk.db")]
    end

    UI --> MAIN
    CURL --> MAIN
    MAIN --> ROUTES --> DEPS
    ROUTES --> USVC
    ROUTES --> ASVC

    USVC --> USTATE
    USVC --> USNAP --> UTRIAGE
    USNAP --> USPEC
    USPEC --> WFLOW

    ASVC --> ASTATE
    ASVC --> ATRIAGE
    ATRIAGE --> ASPEC

    DEPS --> CAT
    DEPS --> UCR
    DEPS --> TKT

    CAT --> DB
    UCR --> DB
    TKT --> DB
    DB --> SQLITE

    USPEC --> MODELS
    ASPEC --> TEMPLATE
    WFLOW --> LANG
```

## API surface map

```mermaid
flowchart LR
    HEALTH["GET /api/health"]

    subgraph UserAssistant["User assistant"]
        UCHAT["POST /api/user/assistant/chat"]
        USTREAM["POST /api/user/assistant/chat/stream"]
        URESET["POST /api/user/assistant/reset"]
        UCHATLEGACY["POST /api/chat (legacy)"]
        USTREAMLEGACY["POST /api/chat/stream (legacy)"]
        URESETLEGACY["POST /api/reset (legacy)"]
    end

    subgraph AdminAssistant["Admin assistant"]
        ACHAT["POST /api/admin/assistant/chat"]
        ARESET["POST /api/admin/assistant/reset"]
    end

    subgraph AdminCatalog["Admin catalog + registry"]
        STEP["GET /api/admin/steps"]
        CATS["/api/admin/categories*"]
        USECASES["/api/admin/use-cases*"]
        TICKETS["GET /api/admin/tickets"]
        TICKETDETAIL["GET /api/admin/tickets/{ticket_id}"]
        APPROVE["POST /api/admin/tickets/{ticket_id}/approve"]
        REJECT["POST /api/admin/tickets/{ticket_id}/reject"]
        RESEED["POST /api/admin/bootstrap/reseed-defaults"]
    end

    HEALTH --> UserAssistant
    HEALTH --> AdminAssistant
    HEALTH --> AdminCatalog
```

## User assistant interaction

```mermaid
sequenceDiagram
    participant U as User
    participant API as /api/user/assistant/chat(_stream)
    participant S as user_assistant/service.py
    participant T as Help Desk Triage Agent
    participant SP as Specialist Agent
    participant W as execute_use_case_workflow
    participant TR as TicketRepository

    U->>API: message + optional conversation_id
    API->>S: validate + route request
    S->>S: load/create conversation state
    S->>T: Runner.run / run_streamed
    T-->>SP: handoff when a use-case matches
    SP->>W: execute deterministic workflow tool
    W->>TR: persist ticket, fields, steps, events
    TR-->>W: ticket status pending_review
    W-->>SP: workflow output + pending-review message
    SP-->>S: final assistant response
    S-->>API: events + current agent + conversation state
    API-->>U: response payload / stream events
```

## Admin assistant interaction

```mermaid
sequenceDiagram
    participant A as IT Operator
    participant API as /api/admin/assistant/chat
    participant S as admin_assistant/service.py
    participant T as Tech Team Assistant Triage
    participant C as Category Creator Specialist
    participant L as Category Lifecycle Specialist
    participant R as Repositories

    A->>API: admin instruction + optional conversation_id
    API->>S: validate + route request
    S->>S: load/create conversation state
    S->>T: Runner.run
    T-->>C: handoff for create/publish intents
    T-->>L: handoff for inspect/maintenance intents
    C->>R: list/create/publish category or runbook actions
    L->>R: list/inspect lifecycle actions
    R-->>S: operation results
    S-->>API: events + current agent + updated state
    API-->>A: response payload
```

## Ticket lifecycle

```mermaid
stateDiagram-v2
    [*] --> open: start_workflow_execution
    open --> in_progress: workflow_started
    in_progress --> pending_review: workflow completed
    in_progress --> in_progress: workflow_failed
    pending_review --> approved: IT approve
    pending_review --> rejected: IT reject
    approved --> [*]
    rejected --> [*]
```

## Run + validate

```mermaid
flowchart TD
    START["From repo root (`help-desk-agent/`)"]
    ENV["Create backend/.env with OPENAI_API_KEY"]
    RUN["uv run --env-file backend/.env python -m backend.api.main"]
    HEALTH["curl http://127.0.0.1:8000/api/health"]
    CHECKS["uv run ruff check backend\nuv run mypy backend\nuv run pytest backend/tests -q"]

    START --> ENV --> RUN --> HEALTH --> CHECKS
```
