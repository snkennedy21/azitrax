# Vector

Minimal geospatial app exploring the smallest useful loop:

UI -> API -> DB -> API -> UI

The Phase 0 goal is for a user to open a map, click to save a point, and see persisted points rendered from PostGIS.

## Project Layout

- `frontend/`: React app. This will render the map, handle map clicks, call the backend API, and draw saved points.
- `backend/`: FastAPI app. This will expose point endpoints, run SQL, and communicate with Postgres/PostGIS.
- `compose.yaml`: Local Postgres/PostGIS service configuration for development.
- `minimal_geospatial_design.md`: Phase 0 design and architecture notes.
- `github_issues_phase_0.md`: Initial GitHub issue backlog derived from the Phase 0 design.

## Local Services

The first local service is Postgres with PostGIS, defined in `compose.yaml`.

```sh
docker compose up -d db
```

Local defaults are documented in `.env.example`:

- database: `vector`
- user: `vector`
- password: `vector`
- port: `5432`

To override them, create a local `.env` file using the same variable names:

```sh
cp .env.example .env
```

Verify the database accepts connections and PostGIS is enabled:

```sh
docker compose exec db psql -U vector -d vector -c "SELECT PostGIS_Version();"
```

The frontend and backend apps are intentionally not scaffolded yet. Their directories exist to establish the repository layout for upcoming tickets.
