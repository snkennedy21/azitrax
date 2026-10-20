from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from psycopg import Error as PsycopgError

from app.db.connection import DbConnection
from app.queries.vessel_history import list_recent_history
from app.schemas.points import PointListItem


router = APIRouter(prefix="/vessels")


@router.get("/{mmsi}/history")
def get_vessel_history(
    db: DbConnection,
    mmsi: int,
    minutes: int = Query(default=30, ge=1),
) -> list[PointListItem]:
    try:
        rows = list_recent_history(db, mmsi=mmsi, minutes=minutes)
    except PsycopgError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    return [
        PointListItem(
            id=row.id,
            lat=row.lat,
            lon=row.lon,
        )
        for row in rows
    ]
