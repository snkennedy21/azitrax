from dataclasses import dataclass

from psycopg import Connection
from psycopg.rows import DictRow


@dataclass(frozen=True)
class PointQueryRow:
    id: int
    lat: float
    lon: float


def list_points(db: Connection[DictRow]) -> list[PointQueryRow]:
    rows = db.execute(
        """
        SELECT
            id,
            ST_Y(geom) AS lat,
            ST_X(geom) AS lon
        FROM points
        ORDER BY id
        """
    ).fetchall()

    return [
        PointQueryRow(
            id=row["id"],
            lat=row["lat"],
            lon=row["lon"],
        )
        for row in rows
    ]
