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

## Verification

Use the production build as the baseline frontend confidence check:

```sh
npm run build
```

This runs `tsc -b` before `vite build`, so TypeScript compilation must pass
before the app bundles. Generated API types participate in this check through
`src/services/api/type-helpers.ts`, which imports
`src/services/api/types.generated.ts` and re-exports the public API aliases used
by the React Query hooks.

Frontend unit or component tests are intentionally deferred for now. Add a test
runner when there is a clear target for behavior that is not already covered by
the TypeScript build and Vite bundle checks.

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
React Query. In create-point mode, map clicks save points through the backend API
and persisted points render as markers when the browser reloads.

For the current manual browser checklist, see
[../docs/smoke-test.md](../docs/smoke-test.md).
