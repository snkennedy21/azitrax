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

## Current Scope

The app currently renders a minimal React entry point. OpenLayers setup, API
calls, point rendering, and map click handling are not implemented yet.
