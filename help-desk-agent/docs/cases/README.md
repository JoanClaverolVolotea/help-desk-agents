# Case Examples and Default Mapping

This folder stores source ticket examples used to shape the default category and use-case catalog.

## Normalized summaries

### `USDV-176285` (`[USDV-176285] ... Log in problem into eCrew - Jira.pdf`)

- Pattern: access reset / login recovery.
- Request shape: requester cannot access eCrew and needs recovery/unlock/reset actions.
- Key identifiers seen in the case: ticket ID (`USDV-176285`), requester details, internal requester ID.

### `USDV-176893` (`[USDV-176893] ALTAS E-MAIL_EFOS_PELESYS 16-02-2026 - Jira.pdf`)

- Pattern: onboarding setup.
- Request shape: onboarding request to provision accounts in E-MAIL, EFOS, and PELESYS.
- Key identifiers seen in the case: ticket ID (`USDV-176893`), requester, one or more employees, target systems.

## Mapping used by seeded defaults

- Case pattern: eCrew login/access issue
  Category: `access-reset`
  Use case: `reset-acceso-ecrew`
  Required fields: `ticket_id`, `requester_name`, `requester_id`, `affected_platforms`

- Case pattern: onboarding E-MAIL/EFOS/PELESYS
  Category: `employee-onboarding`
  Use case: `alta-email-efos-pelesys`
  Required fields: `ticket_id`, `requester_name`, `employee_name`, `employee_batch`, `target_systems`
