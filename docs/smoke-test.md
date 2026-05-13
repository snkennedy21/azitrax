# Phase 0 Manual Smoke Test

Use this checklist to verify the current browser workflow after starting the local
services. It covers the implemented OpenLayers map, API health indicator, point
creation mode, and persisted point rendering.

## Start Local Services

From the repository root, start the frontend, backend, and PostGIS database:

```sh
docker compose up --build frontend backend
```

The backend service depends on the `db` service, so Compose starts Postgres with
PostGIS automatically.

Wait until the backend logs indicate startup is complete and the frontend logs
show the Vite dev server is ready before opening the browser.

Expected local URLs:

- Frontend: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000`
- Backend health: `http://127.0.0.1:8000/health`
- Database health: `http://127.0.0.1:8000/health/db`

## Checklist

1. Open `http://127.0.0.1:5173` in a browser.
   - If the page was already open while services were still starting, refresh it
     once after the backend is ready.
2. Verify the map loads.
   - Expected: a dark OpenLayers basemap appears with visible map tiles.
   - Expected: the map can be dragged and zoomed with standard browser map
     interactions.
3. Verify the API status indicator reports a connected state.
   - Expected: the status indicator on the map reads `API connected`.
4. Enable create-point mode.
   - Click the map mode button with the `Add Points` tooltip.
   - Expected: the button switches from the hand icon to the location marker
     icon, indicating add-points mode is active.
5. Click the map to create a point.
   - Expected: a blue circular point marker appears at the clicked location.
6. Refresh the browser.
   - Expected: the point marker still appears after reload, confirming the point
     was persisted through the API and PostGIS.
7. Optional API confirmation:

```sh
curl http://127.0.0.1:8000/points
```

Expected: the response contains the point you created, with `id`, `lat`, and
`lon` fields.

## Troubleshooting

If the map appears but the status indicator does not reach `API connected`, check
that the backend is running and reachable:

```sh
curl http://127.0.0.1:8000/health
```

If the backend is running but points fail to load or save, verify database
connectivity and PostGIS availability:

```sh
curl http://127.0.0.1:8000/health/db
docker compose logs backend db
```

If the map container loads but tiles are blank, confirm the browser can reach the
configured external tile provider. Point creation can still be checked against
the vector marker layer once the API and database are healthy.
