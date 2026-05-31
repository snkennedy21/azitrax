from fastapi import APIRouter
from fastapi import HTTPException
from psycopg import Error as PsycopgError

from app.db.connection import DbConnection
from app.schemas.points import PointCreate
from app.schemas.points import PointListItem
from app.schemas.points import PointResponse


router = APIRouter(prefix="/points")


@router.post("", status_code=201)
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


@router.get("")
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
