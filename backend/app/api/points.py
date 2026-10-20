from fastapi import APIRouter
from fastapi import HTTPException
from psycopg import Error as PsycopgError

from app.db.connection import DbConnection
from app.queries.points import list_points
from app.schemas.points import PointListItem


router = APIRouter(prefix="/points")


@router.get("")
def get_points(db: DbConnection) -> list[PointListItem]:
    try:
        rows = list_points(db)
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
