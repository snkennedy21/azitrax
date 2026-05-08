# Frontend

React client for the minimal geospatial app.

## Local Development

Start the frontend in Docker:

```sh
docker compose up --build frontend
```

Open `http://127.0.0.1:5173`.

The container installs dependencies with `npm ci` during the image build. The
source directory is mounted into the container for local development, while
`node_modules` stays inside a Docker volume.

## API Configuration

The frontend reads `VITE_API_BASE_URL` for API requests. The default is `/api`,
which Vite proxies to the backend so browser requests stay same-origin during
local development.

Expected local backend URL:

- Docker Compose frontend: `http://backend:8000`
- Host-run frontend: `http://127.0.0.1:8000`

Environment variables:

- `VITE_API_BASE_URL`: frontend API base path or URL. Defaults to `/api`.
- `VITE_API_PROXY_TARGET`: Vite dev proxy target for `/api`. Defaults to
  `http://127.0.0.1:8000` when running Vite directly; Compose sets it to
  `http://backend:8000`.

## Current Scope

The app currently renders the OpenLayers map and checks backend health through
React Query. Point rendering and map click handling are not implemented yet.
