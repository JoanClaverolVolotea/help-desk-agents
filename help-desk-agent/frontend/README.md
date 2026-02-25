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

Frontend calls backend APIs through `src/api.js`.

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

- `src/routes/AppRoutes.jsx`: route tree
- `src/pages/`: page components
- `src/components/`: reusable UI components
- `src/api.js`: backend API client helpers
- `src/utils/`: payload and UI helper functions
- `src/App.css`: styling
