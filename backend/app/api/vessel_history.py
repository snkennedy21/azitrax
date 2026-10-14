from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from psycopg import Error as PsycopgError

from app.db.connection import DbConnection
from app.schemas.points import PointListItem


router = APIRouter(prefix="/vessels")


@router.get("/{mmsi}/history")
def get_vessel_history(
    db: DbConnection,
    mmsi: int,
    minutes: int = Query(default=30, ge=1),
) -> list[PointListItem]:
    sql = """
        SELECT
            id,
            ST_Y(position) AS lat,
            ST_X(position) AS lon
        FROM vessel_history
        WHERE mmsi = %s
          AND observed_at >= NOW() - make_interval(mins => %s)
        ORDER BY observed_at, id
    """

    try:
        rows = db.execute(sql, (mmsi, minutes)).fetchall()
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
