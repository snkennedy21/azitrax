# Vector

Minimal geospatial app exploring the smallest useful loop:

UI -> API -> DB -> API -> UI

The Phase 0 goal is for a user to open a map, click to save a point, and see persisted points rendered from PostGIS.

## Project Layout

- `frontend/`: React app that renders the map, handles map clicks, calls the backend API, and draws saved points.
- `backend/`: FastAPI app that exposes point endpoints, runs SQL, and communicates with Postgres/PostGIS.
- `compose.yaml`: Local frontend, backend, Postgres/PostGIS, and pgAdmin service configuration for development.
- `docs/smoke-test.md`: Manual browser smoke test for the Phase 0 map workflow.
- `minimal_geospatial_design.md`: Phase 0 design and architecture notes.
- `github_issues_phase_0.md`: Initial GitHub issue backlog derived from the Phase 0 design.

## Local Services

Local services are defined in `compose.yaml`.

Start the frontend:

```sh
docker compose up --build frontend
```

Open the React app at `http://127.0.0.1:5173`.

In development the frontend calls the API through Vite's `/api` proxy by
default. The expected local backend URL is `http://127.0.0.1:8000` when running
on the host, or `http://backend:8000` from the Compose frontend container.

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
- AIS source mode: `fixture`
- AIS fallback fixture path: `docs/fixtures/aisstream-position-reports-sample.json`
- AIS fixture fallback after live-source failure: `true`
- AISStream WebSocket URL: `wss://stream.aisstream.io/v0/stream`
- AISStream API key: unset by default; set it for live discovery
- AISStream bounding boxes: `[[[40.4774,-74.2591],[40.9176,-73.7004]]]`
- AISStream message types: `PositionReport`
- AISStream connection timeout: `10` seconds
- AISStream discovery sample limit: `100` messages
- AISStream TLS verification disabled: `false`
- frontend port: `5173`
- backend port: `8000`
- frontend API base URL: `/api`
- frontend API proxy target: `http://backend:8000` in Compose, or `http://127.0.0.1:8000` when running Vite directly on the host
- allowed frontend CORS origins: `http://127.0.0.1:5173,http://localhost:5173`
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

The frontend renders an OpenLayers map, shows backend API health, lets users add
point markers in create-point mode, and reloads persisted points from PostGIS.
For the end-to-end browser checklist, see [docs/smoke-test.md](docs/smoke-test.md).

## Source Discovery

The first live external source for the next discovery phase is AIS vessel
position data from AISStream at `wss://stream.aisstream.io/v0/stream`. Local
development defaults to an AISStream-shaped fixture so developers can work
without network access, credentials, or live service availability.

See [docs/source-discovery.md](docs/source-discovery.md) for the source decision,
authentication expectations, known rate-limit and availability constraints,
payload shape, and the `fixture`/`aisstream` switch.

The frontend can poll `GET /vessels` for current live vessel positions.
The response contains `items` for map rendering and `metadata` with the AIS
source name, UTC fetch time, and returned item count. These records are read
from the configured AIS source and are not persisted.

## Type Generation

The frontend TypeScript types are generated from the backend OpenAPI schema to ensure type safety across the API boundary and eliminate manual type maintenance.

### Regenerating Types

When you modify Pydantic models or API endpoints in the backend:

1. Start the backend:
   ```sh
   docker compose up -d backend
   ```

2. Regenerate frontend types:
   ```sh
   cd frontend
   npm run generate:api-types
   ```

3. Review the changes in [frontend/src/services/api/types.generated.ts](frontend/src/services/api/types.generated.ts)

4. Commit both backend and frontend changes together

### Type Generation Architecture

- **Backend**: Pydantic models in [backend/app/schemas.py](backend/app/schemas.py) with camelCase aliases
- **OpenAPI Schema**: Auto-generated by FastAPI at `http://127.0.0.1:8000/openapi.json`
- **Generated Types**: [frontend/src/services/api/types.generated.ts](frontend/src/services/api/types.generated.ts) (do not edit manually)
- **Type Helpers**: [frontend/src/services/api/type-helpers.ts](frontend/src/services/api/type-helpers.ts) (clean type aliases)
- **Public API**: [frontend/src/services/api/types.ts](frontend/src/services/api/types.ts) (re-exports for components)

### Troubleshooting

**Error: "connect ECONNREFUSED"**
- Solution: Make sure the backend is running on `http://127.0.0.1:8000`

**Error: "Could not resolve openapi.json"**
- Solution: Check that `/openapi.json` endpoint returns valid JSON:
  ```sh
  curl http://127.0.0.1:8000/openapi.json | python3 -m json.tool
  ```

**Types don't match API responses**
- Solution: Ensure you regenerated types after backend changes
- Check that backend uses Pydantic `CamelCaseModel` base class from [backend/app/schemas.py](backend/app/schemas.py)
