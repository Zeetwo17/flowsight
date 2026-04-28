# FlowSight Frontend

Vite + React + TypeScript + Tailwind PWA. Talks to the FastAPI backend
at `localhost:8080` via the Vite dev proxy (`/api`, `/ws`).

## Quickstart

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Run the backend in another terminal:

```bash
cd ..
uvicorn flowsight.api.server:app --reload --port 8080
# (the FastAPI app lives at src/flowsight/api/server.py — make sure src/ is on PYTHONPATH)
```

## Build for production

```bash
npm run build        # outputs ./dist
npm run preview      # serve dist locally
```

The build is a static PWA — deploy to Firebase Hosting, Cloud Storage,
or any static host.

## Configure backend URL

By default the dev server proxies `/api` to `http://localhost:8080`.
For deployment, set `VITE_API_BASE` at build time:

```bash
VITE_API_BASE=https://flowsight-api-xxxx.run.app npm run build
```

## PWA

`vite-plugin-pwa` generates the service worker automatically. The app
installs on iOS/Android home screens and works offline (cached static
assets only — live data still needs the backend).
