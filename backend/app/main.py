from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
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


class PointCreate(BaseModel):
    # Latitude is the north/south coordinate. Valid WGS84 latitude is -90..90.
    lat: float = Field(ge=-90, le=90)

    # Longitude is the east/west coordinate. Valid WGS84 longitude is -180..180.
    lon: float = Field(ge=-180, le=180)


class PointResponse(BaseModel):
    id: int
    lat: float
    lon: float
    srid: int


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
