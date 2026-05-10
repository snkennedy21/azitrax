# Backend

FastAPI service for the minimal geospatial app.

## Local Development

Start the backend without the frontend:

```sh
docker compose up --build backend
```

The API will be available at `http://127.0.0.1:8000`.

Check that it is running:

```sh
curl http://127.0.0.1:8000/health
```

Check that it can connect to Postgres/PostGIS:

```sh
curl http://127.0.0.1:8000/health/db
```

Create a point:

```sh
curl -X POST http://127.0.0.1:8000/points \
  -H "Content-Type: application/json" \
  -d '{"lat": 40.7128, "lon": -74.0060}'
```

## Database Configuration

The backend uses direct SQL through `psycopg` v3. Connection settings are read from environment variables:

- `DATABASE_URL`: optional full Postgres connection URL. When set, it overrides the individual `POSTGRES_*` fields.
- `POSTGRES_HOST`: database host. Defaults to `127.0.0.1` in Python and `db` in Compose.
- `POSTGRES_PORT`: database port. Defaults to `5432`.
- `POSTGRES_DB`: database name. Defaults to `vector`.
- `POSTGRES_USER`: database user. Defaults to `vector`.
- `POSTGRES_PASSWORD`: database password. Defaults to `vector`.
- `POSTGRES_CONNECT_TIMEOUT`: connection timeout in seconds. Defaults to `5`.
- `POSTGRES_POOL_MIN_SIZE`: minimum open connections in the pool. Defaults to `1`.
- `POSTGRES_POOL_MAX_SIZE`: maximum open connections in the pool. Defaults to `5`.
- `POSTGRES_POOL_TIMEOUT`: seconds to wait for an available pooled connection. Defaults to `5`.
- `FRONTEND_ORIGINS`: comma-separated origins allowed by CORS. Defaults to `http://127.0.0.1:5173,http://localhost:5173`.

Use parameterized SQL for any query that includes external input:

```py
def get_point(db: DbConnection):
    row = db.execute(
        "SELECT id FROM points WHERE id = %s",
        (point_id,),
    ).fetchone()
```

## Testing

The backend uses pytest for testing with a separate test database for isolation.

### Setup

1. The `vector_test` database is created automatically when you start Docker Compose (via init script in `db-init/`)

2. Install test dependencies:
   ```sh
   pip install -r requirements.txt
   ```

### Running Tests

**Local** (from `/backend` directory):
```sh
# Set test database environment variables
export TEST_POSTGRES_HOST=127.0.0.1
export TEST_POSTGRES_DB=vector_test

# Run all tests
pytest

# Run specific test file
pytest tests/test_health.py

# Run with verbose output
pytest -v
```

**Docker**:
```sh
# Run tests in backend container
docker compose exec backend pytest

# Run with verbose output
docker compose exec backend pytest -v
```

### Test Structure

- `tests/conftest.py` - Shared fixtures (database pool, client, cleanup)
- `tests/test_health.py` - Health endpoint tests
- `pytest.ini` - Pytest configuration

### Database Isolation

Tests run against a separate `vector_test` database. Each test automatically cleans up data using `TRUNCATE TABLE` to ensure isolation between tests.
