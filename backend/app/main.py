from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from datetime import timezone
import os

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg import Error as PsycopgError

from app.ais_source import AisSourceError
from app.ais_source import AisSourceConfig
from app.ais_source import load_ais_vessel_records
from app.ais_source import map_live_vessel_items
from app.database import create_pool
from app.database import DbConnection
from app.migrations import run_migrations
from app.migrations import validate_migrations
from app.schemas import LiveVesselsMetadata
from app.schemas import LiveVesselsResponse
from app.schemas import PointCreate
from app.schemas import PointListItem
from app.schemas import PointResponse


# FastAPI calls this function once when the app starts and resumes it once
# when the app shuts down. That makes it a good home for resources that should
# live for the whole process, like a database connection pool.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Run database migrations before opening connection pool.
    # This ensures schema is up-to-date before any API requests are processed.
    try:
        validate_migrations()
        run_migrations()
    except RuntimeError as exc:
        # Migration failures are fatal - log error and exit.
        # Docker will restart the container, retrying until migrations succeed.
        print(f"Fatal error during database migrations: {exc}")
        raise

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

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    # This endpoint only proves the HTTP server is alive.
    # It does not touch Postgres.
    return {"status": "ok"}


@app.get("/vessels")
async def get_vessels() -> LiveVesselsResponse:
    try:
        config = AisSourceConfig.from_env()
        records = await load_ais_vessel_records(config)
    except AisSourceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    items = map_live_vessel_items(records)
    return LiveVesselsResponse(
        items=items,
        metadata=LiveVesselsMetadata(
            source=config.source,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            returned_count=len(items),
        ),
    )


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


@app.post("/points", status_code=201)
def create_point(point: PointCreate, db: DbConnection) -> PointResponse:
    # PostGIS points are stored as X/Y coordinates. For geographic coordinates,
    # X is longitude and Y is latitude, so ST_MakePoint must receive lon first.
    sql = """
        INSERT INTO points (geom)
        VALUES (ST_SetSRID(ST_MakePoint(%s, %s), 4326))
        RETURNING
            id,
            ST_Y(geom) AS lat,
            ST_X(geom) AS lon,
            ST_SRID(geom) AS srid
    """

    try:
        # Parameters are passed separately from the SQL string. psycopg sends
        # them safely to Postgres instead of interpolating them into the text.
        row = db.execute(sql, (point.lon, point.lat)).fetchone()
    except PsycopgError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    if row is None:
        raise HTTPException(status_code=500, detail="point was not saved")

    return PointResponse(
        id=row["id"],
        lat=row["lat"],
        lon=row["lon"],
        srid=row["srid"],
    )


@app.get("/points")
def get_points(db: DbConnection) -> list[PointListItem]:
    sql = """
        SELECT
            id,
            ST_Y(geom) AS lat,
            ST_X(geom) AS lon
        FROM points
        ORDER BY id
    """

    try:
        rows = db.execute(sql).fetchall()
    except PsycopgError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    return [
        PointListItem(
            id=row["id"],
            lat=row["lat"],
            lon=row["lon"],
        )
        for row in rows
    ]
