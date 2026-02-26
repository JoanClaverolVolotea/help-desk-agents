# Help Desk Frontend

React + Vite frontend for the Help Desk Agent PoC.

It includes:

- Role landing page
- User portal chat
- IT console:
  - Routing policies (categories)
  - Runbooks (use-cases)
  - Ticket registry
  - Persistent tech assistant panel

## Stack

- React 18
- React Router
- Vite 5

## Requirements

- Node.js + npm

## Install and run

From `help-desk-agent/frontend/`:

```bash
npm install
npm run dev
```

Default UI URL:

- `http://127.0.0.1:5173`

## Environment

Frontend calls backend APIs through context clients:

- `src/features/user_assistant/api/userAssistantClient.ts`
- `src/features/admin_assistant/api/adminAssistantClient.ts`
- `src/features/admin_assistant/api/adminCatalogClient.ts`

- Default API base URL: `http://127.0.0.1:8000`
- Override with:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Example:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## Route map

- `/`: role landing
- `/user`: user portal
- `/it/dashboard`: IT console dashboard
- `/it/admin/categories`: routing policy management
- `/it/admin/tickets`: ticket registry
- `/it/admin/use-cases`: runbook management
- `/it/assistant`: alias to IT dashboard (assistant stays visible in the console panel)

## Build and preview

From `help-desk-agent/frontend/`:

```bash
npm run build
npm run preview
```

## Source map

- `src/app/`: app bootstrap and route composition
- `src/features/user_assistant/`: user chat pages and API client
- `src/features/admin_assistant/`: admin console pages, components, API clients, and admin-only types/utils
- `src/shared/`: shared i18n, shared UI primitives, shared API helpers, and shared types/utils
- `src/styles/`: `shared.css`, `user_assistant.css`, and `admin_assistant.css`
