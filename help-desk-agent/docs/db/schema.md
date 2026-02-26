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
      text slug UK
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
      text slug UK
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
      text status "open|in_progress|pending_review|approved|rejected"
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
      text status "open|in_progress|pending_review|approved|rejected"
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

## Category vs Use Case

- `Category` (`categories` + `category_versions`): routing template and policy family. It defines the allowed deterministic step IDs and the default handoff/routing/required-field contract for a problem domain.
- `Use case` (`use_cases` + `use_case_versions`): concrete executable workflow in that category. It defines the exact ordered steps and required fields that specialist agents collect and execute.

In practice:

- Category answers: "What type of ticket is this and what workflow patterns are allowed?"
- Use case answers: "Which exact deterministic steps will run for this ticket?"

## Default Catalog (Case-Aligned)

| Case ID | Category slug | Default use-case slug | Pattern | Required fields |
| --- | --- | --- | --- | --- |
| `USDV-176285` | `access-reset` | `reset-acceso-ecrew` | eCrew login/access recovery | `ticket_id`, `requester_name`, `requester_id`, `affected_platforms` |
| `USDV-176893` | `employee-onboarding` | `alta-email-efos-pelesys` | Employee onboarding for E-MAIL/EFOS/PELESYS | `ticket_id`, `requester_name`, `employee_name`, `employee_batch`, `target_systems` |

## Ticket lifecycle

- Ticket row is created when deterministic workflow execution starts.
- Initial transitions are `open -> in_progress`.
- Successful deterministic execution transitions to `pending_review`.
- IT review transitions `pending_review -> approved` or `pending_review -> rejected`.
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
