from fastapi import APIRouter
from fastapi import HTTPException
from psycopg import Error as PsycopgError

from app.db.connection import DbConnection
from app.schemas.points import PointListItem


router = APIRouter(prefix="/points")


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
