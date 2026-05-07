# Phase 0 GitHub Issue Backlog

This backlog breaks the Phase 0 design into small tickets that progress naturally toward the core loop:

UI -> API -> DB -> API -> UI

Each ticket is intentionally narrow. Later tickets should assume earlier tickets are complete.

---

## 1. Scaffold local project structure

### Goal
Create the initial repository layout for the frontend, backend, and local database configuration.

### Scope
- Add a `frontend/` directory for the React app.
- Add a `backend/` directory for the FastAPI app.
- Add a local orchestration file for Postgres/PostGIS.
- Add a short root README section describing the project layout.

### Acceptance Criteria
- Repository has clear `frontend/` and `backend/` directories.
- A developer can tell where app, API, and database setup will live.
- No app behavior is required yet.

---

## 2. Add local PostGIS database service

### Goal
Run Postgres with PostGIS locally.

### Scope
- Configure a Postgres/PostGIS container.
- Set database name, user, and password through local environment variables or documented defaults.
- Make the service startable with one local command.

### Acceptance Criteria
- Local PostGIS service starts successfully.
- The database accepts connections.
- PostGIS extension is available in the database.

---

## 3. Create the `points` database table

### Goal
Add the minimal schema needed to store clicked map points.

### Scope
- Create a `points` table.
- Include `id`, `geom`, and `created_at` columns.
- Use `GEOMETRY(Point, 4326)` for `geom`.
- Ensure the schema can be applied locally.

### Acceptance Criteria
- `points` table exists in the local database.
- `geom` stores WGS84 point geometry.
- `created_at` defaults to the current timestamp.

### Reference SQL
```sql
CREATE TABLE points (
  id SERIAL PRIMARY KEY,
  geom GEOMETRY(Point, 4326),
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. Scaffold FastAPI backend

### Goal
Create a minimal FastAPI app that can run locally.

### Scope
- Add backend dependency management.
- Create a FastAPI application entry point.
- Add a simple health check endpoint.
- Document how to start the backend locally.

### Acceptance Criteria
- Backend starts locally.
- Health check endpoint returns a successful response.
- Backend can be run without the frontend.

---

## 5. Add backend database connection layer

### Goal
Allow the FastAPI backend to connect to Postgres/PostGIS.

### Scope
- Add a thin database access module.
- Use direct SQL through `psycopg` v3 or SQLAlchemy Core.
- Read connection configuration from environment variables.
- Avoid ORM models.

### Acceptance Criteria
- Backend can open a database connection.
- Database connection configuration is documented.
- Queries use parameterized SQL where inputs are involved.

---

## 6. Implement `POST /points`

### Goal
Persist a clicked map point in PostGIS.

### Scope
- Add `POST /points`.
- Accept JSON with `lat` and `lon`.
- Insert the point using longitude-first PostGIS ordering.
- Return the saved point or a simple success response.

### Acceptance Criteria
- Valid `lat` and `lon` values create a row in `points`.
- Stored geometry uses SRID 4326.
- Longitude and latitude are not reversed.
- SQL uses parameters rather than string interpolation.

### Reference SQL
```sql
INSERT INTO points (geom)
VALUES (ST_SetSRID(ST_MakePoint(:lon, :lat), 4326));
```

---

## 7. Implement `GET /points`

### Goal
Return all persisted points to the frontend.

### Scope
- Add `GET /points`.
- Query all rows from the `points` table.
- Return each point as `id`, `lat`, and `lon`.

### Acceptance Criteria
- Endpoint returns a JSON array.
- Each item includes `id`, `lat`, and `lon`.
- Latitude is read with `ST_Y(geom)`.
- Longitude is read with `ST_X(geom)`.

### Reference Response
```json
[
  {
    "id": 1,
    "lat": 38.9,
    "lon": -77.0
  }
]
```

---

## 8. Add basic backend API tests

### Goal
Verify the point API behavior before connecting the frontend.

### Scope
- Add tests for `POST /points`.
- Add tests for `GET /points`.
- Include at least one assertion that protects against latitude/longitude reversal.

### Acceptance Criteria
- Tests can be run locally with one command.
- Tests verify that a posted point can be read back.
- Tests cover the expected response shape.

---

## 9. Scaffold React frontend

### Goal
Create a minimal React app that can run locally.

### Scope
- Add frontend dependency management.
- Add a basic app entry point.
- Document how to start the frontend locally.

### Acceptance Criteria
- Frontend starts locally.
- Browser displays the React app.
- No map behavior is required yet.

---

## 10. Render an OpenLayers map

### Goal
Display a map using OpenLayers and OpenStreetMap tiles.

### Scope
- Install and configure OpenLayers.
- Render a map in the main React view.
- Use OpenStreetMap tiles.
- Choose an initial center and zoom.

### Acceptance Criteria
- Map loads in the browser.
- OpenStreetMap tiles are visible.
- Map can be panned and zoomed.

---

## 11. Fetch and render saved points on the map

### Goal
Render persisted database points as map markers.

### Scope
- Call `GET /points` when the frontend loads.
- Store returned points in frontend state.
- Convert WGS84 coordinates to the map projection.
- Render one OpenLayers feature per point.

### Acceptance Criteria
- Existing database points appear on the map.
- Each returned point is represented once.
- Points are rendered in the correct geographic location.

---

## 12. Save a point when the user clicks the map

### Goal
Complete the click-to-save behavior.

### Scope
- Listen for map click events.
- Convert clicked map coordinates from Web Mercator to WGS84.
- Send clicked coordinates to `POST /points`.
- Refetch points after the write succeeds.

### Acceptance Criteria
- Clicking the map creates a new point in the database.
- Newly created point appears on the map after the refetch.
- Frontend sends coordinates as `lat` and `lon`.
- No optimistic update is used.

---

## 13. Wire frontend and backend configuration

### Goal
Make the frontend API target configurable for local development.

### Scope
- Add frontend configuration for the backend base URL.
- Document the expected local backend URL.
- Ensure CORS or local dev proxy behavior allows frontend/backend communication.

### Acceptance Criteria
- Frontend can call the local backend in development.
- API base URL is not hard-coded in multiple places.
- Local setup instructions mention any required environment variables.

---

## 14. Add end-to-end local smoke test instructions

### Goal
Document the manual test that proves Phase 0 works.

### Scope
- Add instructions for starting database, backend, and frontend.
- Add a short smoke test checklist.
- Include expected behavior after refresh.

### Acceptance Criteria
- A developer can follow the instructions from a clean checkout.
- Checklist verifies that the map loads.
- Checklist verifies that clicking creates a point.
- Checklist verifies that refreshing still shows the point.

---

## 15. Phase 0 completion check

### Goal
Confirm the minimum geospatial loop is complete.

### Scope
- Run the documented local setup.
- Execute backend tests.
- Manually verify the browser behavior.
- Record any known limitations or follow-up work.

### Acceptance Criteria
- Map loads.
- Click creates a point.
- Refresh persists the point.
- Points are read from PostGIS.
- Non-goals remain out of scope: auth, realtime updates, caching, performance tuning, and UI polish.
