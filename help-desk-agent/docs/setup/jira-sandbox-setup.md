# Jira Sandbox Setup (Personal Account)

This guide helps you create a personal Jira Cloud sandbox and connect it to `help-desk-agent/` so you can build and validate automation before corporate PRE access is available.

## Scope

- Focus: agent-side integration and ticket editing lifecycle.
- Target API: Jira Cloud REST API v3.
- Auth mode: Basic auth with Atlassian account email + API token.

## 1) Create a free Jira Cloud site

1. Open `https://www.atlassian.com/software/jira/free`.
2. Sign up with your personal email.
3. Create a site, for example `https://yourname.atlassian.net`.
4. Store this value as `JIRA_BASE_URL`.

## 2) Create a project for automation tests

1. In Jira, create a new project (team-managed is fine for sandbox use).
2. Choose a simple template (Kanban recommended).
3. Set a project key, for example `HD`.
4. Keep default issue types (`Task`, `Bug`) unless you need custom ones.

Store project key as `JIRA_PROJECT_KEY`.

## 3) Create an Atlassian API token

1. Open `https://id.atlassian.com/manage-profile/security/api-tokens`.
2. Click **Create API token**.
3. Name it, for example `help-desk-agent-dev`.
4. Set expiry (max is 365 days).
5. Copy token immediately and store it safely.

Store:
- Atlassian login email as `JIRA_EMAIL`
- Token as `JIRA_API_TOKEN`

## 4) Configure backend environment

Edit `help-desk-agent/backend/.env` and add:

```dotenv
JIRA_CLIENT_MODE=http
JIRA_BASE_URL=https://yourname.atlassian.net
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=your_api_token_here
JIRA_PROJECT_KEY=HD
```

Notes:
- Keep `.env` local only.
- Never commit tokens.

## 5) Verify credentials and API connectivity

Run these checks from your terminal (replace values):

```bash
curl -sS -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" \
  "${JIRA_BASE_URL}/rest/api/3/myself"
```

Expected: JSON with your account profile.

```bash
curl -sS -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" \
  "${JIRA_BASE_URL}/rest/api/3/project/${JIRA_PROJECT_KEY}"
```

Expected: JSON containing project metadata.

## 6) Create a test issue

```bash
curl -sS -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -X POST \
  "${JIRA_BASE_URL}/rest/api/3/issue" \
  -d '{
    "fields": {
      "project": {"key": "HD"},
      "summary": "Help Desk sandbox test issue",
      "description": {
        "type": "doc",
        "version": 1,
        "content": [
          {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Created for automation validation."}]
          }
        ]
      },
      "issuetype": {"name": "Task"}
    }
  }'
```

Expected: JSON with `key` (for example `HD-1`).

## 7) Add comment and transition issue

Add comment:

```bash
curl -sS -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -X POST \
  "${JIRA_BASE_URL}/rest/api/3/issue/HD-1/comment" \
  -d '{
    "body": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "paragraph",
          "content": [{"type": "text", "text": "Automation test comment."}]
        }
      ]
    }
  }'
```

List transitions:

```bash
curl -sS -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" \
  "${JIRA_BASE_URL}/rest/api/3/issue/HD-1/transitions"
```

Use one returned transition ID:

```bash
curl -sS -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -X POST \
  "${JIRA_BASE_URL}/rest/api/3/issue/HD-1/transitions" \
  -d '{"transition": {"id": "31"}}'
```

## 8) Recommended implementation order (updated)

Because you now have a personal Jira Cloud sandbox, use this order:

1. M1 Protocol and shared models (done).
2. M2 In-memory client.
3. M3 Configuration and dependency wiring.
4. M6 HTTP Jira client (move earlier, validate against sandbox).
5. M4 Replace simulated workflow step actions.
6. M5 Sync admin approve/reject with Jira transitions.
7. M7 Admin assistant Jira tools.

## 9) Troubleshooting

- `401 Unauthorized`: check email/token pair and token expiration.
- `403 Forbidden`: account lacks permission in project.
- `404 Not Found`: wrong base URL, wrong project key, or wrong issue key.
- `400 Bad Request` on description/comment: use Atlassian Document Format for v3 endpoints.
- CAPTCHA lockout after failed logins: reset via web login, then retry API.

## 10) Security checklist

- Use a dedicated token for this project.
- Set reminder before token expiry.
- Rotate token if it is exposed.
- Keep secrets only in local `.env` or secret manager.

## 11) Later switch to corporate PRE

When PRE access arrives, only replace:

- `JIRA_BASE_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_PROJECT_KEY`

No agent/workflow code changes should be required if integration remains protocol-driven.
