# Vector

Minimal geospatial app exploring the smallest useful loop:

UI -> API -> DB -> API -> UI

The Phase 0 goal is for a user to open a map, click to save a point, and see persisted points rendered from PostGIS.

## Project Layout

- `frontend/`: React app. This will render the map, handle map clicks, call the backend API, and draw saved points.
- `backend/`: FastAPI app. This will expose point endpoints, run SQL, and communicate with Postgres/PostGIS.
- `compose.yaml`: Local frontend, backend, Postgres/PostGIS, and pgAdmin service configuration for development.
- `minimal_geospatial_design.md`: Phase 0 design and architecture notes.
- `github_issues_phase_0.md`: Initial GitHub issue backlog derived from the Phase 0 design.

## Local Services

Local services are defined in `compose.yaml`.

Start the frontend:

```sh
docker compose up --build frontend
```

Open the React app at `http://127.0.0.1:5173`.

Start the backend API without the frontend:

```sh
docker compose up --build backend
```

Check the backend health endpoint:

```sh
curl http://127.0.0.1:8000/health
```

Start Postgres with PostGIS:

```sh
docker compose up -d db
```

Start Postgres with PostGIS and pgAdmin:

```sh
docker compose up -d db pgadmin
```

Local defaults are documented in `.env.example`:

- database host: `db` from Compose, or `127.0.0.1` when running the backend directly on the host
- database: `vector`
- user: `vector`
- password: `vector`
- database port: `5432`
- database connection timeout: `5` seconds
- database pool size: `1` minimum, `5` maximum
- database pool wait timeout: `5` seconds
- frontend port: `5173`
- backend port: `8000`
- pgAdmin URL: `http://127.0.0.1:5050`
- pgAdmin email: `admin@example.com`
- pgAdmin password: `vector`

To override them, create a local `.env` file using the same variable names:

```sh
cp .env.example .env
```

Verify the database accepts connections and PostGIS is enabled:

```sh
docker compose exec db psql -U vector -d vector -c "SELECT PostGIS_Version();"
```

Verify the backend can connect to Postgres/PostGIS:

```sh
curl http://127.0.0.1:8000/health/db
```

Connect pgAdmin to PostGIS:

1. Open `http://127.0.0.1:5050`.
2. Sign in with email `admin@example.com` and password `vector`.
3. Select `Add New Server`.
4. On the `General` tab, set `Name` to `vector`.
5. On the `Connection` tab, use:
   - `Host name/address`: `db`
   - `Port`: `5432`
   - `Maintenance database`: `vector`
   - `Username`: `vector`
   - `Password`: `vector`
6. Save the server. The `vector` database should appear in the browser tree.

The frontend currently mounts a minimal React app only. Map behavior is intentionally left for upcoming tickets.
