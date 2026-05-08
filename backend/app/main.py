from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException
from psycopg import Error as PsycopgError

from app.database import create_pool
from app.database import DbConnection


# FastAPI calls this function once when the app starts and resumes it once
# when the app shuts down. That makes it a good home for resources that should
# live for the whole process, like a database connection pool.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Build the pool from environment variables in app.database.DatabaseConfig.
    # This does not run SQL yet; it prepares a reusable pool of connections.
    db_pool = create_pool()

    # Open the pool during startup so connection problems appear immediately
    # when the backend boots instead of surprising the first API request.
    db_pool.open()

    # app.state is FastAPI's place for storing process-wide objects. Later,
    # the database dependency reads this same pool from request.app.state.
    app.state.db_pool = db_pool

    try:
        # yield hands control back to FastAPI. The app serves requests until
        # shutdown, then execution continues in the finally block below.
        yield
    finally:
        # Close all pooled database connections when the backend process exits.
        db_pool.close()


# Passing lifespan here tells FastAPI to run the startup/shutdown logic above.
app = FastAPI(title="Vector API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    # This endpoint only proves the HTTP server is alive.
    # It does not touch Postgres.
    return {"status": "ok"}


@app.get("/health/db")
def database_health(db: DbConnection) -> dict[str, str]:
    # db is provided by FastAPI dependency injection. The DbConnection type
    # points to app.database.get_db_connection, which borrows one connection
    # from the pool for this request and returns it afterward.
    try:
        # psycopg v3 lets a connection execute SQL directly. It returns a
        # cursor, and fetchone() reads the first row from that cursor.
        row = db.execute("SELECT PostGIS_Version() AS postgis_version").fetchone()
    except PsycopgError as exc:
        # Translate database-driver errors into a useful HTTP response.
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    # A SELECT like this should always return one row. If it somehow does not,
    # treat that the same as an unavailable database.
    if row is None:
        raise HTTPException(status_code=503, detail="database unavailable")

    # Rows come back dict-like because database.py configured row_factory=dict_row.
    return {"status": "ok", "postgis_version": row["postgis_version"]}
