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

Use parameterized SQL for any query that includes external input:

```py
def get_point(db: DbConnection):
    row = db.execute(
        "SELECT id FROM points WHERE id = %s",
        (point_id,),
    ).fetchone()
```
