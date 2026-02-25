# Help Desk DB Schema

This schema combines category/use-case lifecycle tables with a normalized ticket registry.

## ER diagram

```mermaid
erDiagram
    CATEGORIES ||--o{ CATEGORY_VERSIONS : has_versions
    CATEGORIES ||--o{ USE_CASES : groups
    USE_CASES ||--o{ USE_CASE_VERSIONS : has_versions

    USE_CASES ||--o{ TICKETS : executes
    TICKETS ||--o{ TICKET_STATUS_HISTORY : status_changes
    TICKETS ||--o{ TICKET_FIELDS : extracted_fields
    TICKETS ||--o{ TICKET_STEPS : workflow_steps
    TICKETS ||--o{ TICKET_EVENTS : timeline_events

    CATEGORIES {
      text id PK
      text slug UNIQUE
      text display_name
      text created_at
      text updated_at
      int archived
    }

    CATEGORY_VERSIONS {
      text id PK
      text category_id FK
      int version_number
      text status "draft|published"
      text definition_json
      text created_at
    }

    USE_CASES {
      text id PK
      text slug UNIQUE
      text display_name
      text template_id
      text category_id FK
      int category_version_number
      int is_system_default
      text created_at
      text updated_at
      int archived
    }

    USE_CASE_VERSIONS {
      text id PK
      text use_case_id FK
      int version_number
      text status "draft|published"
      text definition_json
      text created_at
    }

    TICKETS {
      text id PK
      text conversation_id
      text external_ticket_id
      text use_case_id FK
      text status "open|in_progress|resolved"
      text language
      text ticket_context
      text error_message
      text created_at
      text updated_at
      text resolved_at
    }

    TICKET_STATUS_HISTORY {
      text id PK
      text ticket_id FK
      text status "open|in_progress|resolved"
      text changed_at
      text reason
    }

    TICKET_FIELDS {
      text id PK
      text ticket_id FK
      text field_name
      text field_value
      int is_required "0|1"
      text source "provided|derived|missing"
      text created_at
    }

    TICKET_STEPS {
      text id PK
      text ticket_id FK
      int step_order
      text step_id
      text output_text
      text created_at
    }

    TICKET_EVENTS {
      text id PK
      text ticket_id FK
      text event_type
      text agent_name
      text payload_json
      text created_at
    }
```

## Ticket lifecycle

- Ticket row is created when deterministic workflow execution starts.
- Initial transitions are `open -> in_progress`.
- Successful execution transitions to `resolved`.
- Failed execution remains `in_progress` and records failure details in `ticket_events` and `error_message`.

## Lookup indexes

`tickets`:
- `idx_tickets_created_at`
- `idx_tickets_status`
- `idx_tickets_external_ticket_id`
- `idx_tickets_conversation_id`
- `idx_tickets_use_case_id`

Child tables:
- `idx_ticket_status_history_ticket_id`
- `idx_ticket_fields_ticket_id`
- `idx_ticket_steps_ticket_id`
- `idx_ticket_events_ticket_id`
