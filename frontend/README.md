# Frontend

React + Vite app for the AI front-desk demo: landing page, browser calls through the Vapi Web SDK, quote form, win-back campaign, and CRM dashboard.

```bash
cp .env.example .env.local   # VITE_API_URL, default http://localhost:8000/api
npm install
npm run dev                  # http://localhost:5173
npm run lint
npm run build
```

The browser gets the Vapi **public** key and assistant IDs from the backend (`GET /api/vapi/config`); no secrets live in the frontend. See the [root README](../README.md) for the full setup.
