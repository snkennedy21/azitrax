from dataclasses import dataclass

from psycopg import Connection
from psycopg.rows import DictRow


@dataclass(frozen=True)
class VesselHistoryQueryRow:
    id: int
    mmsi: int
    lat: float
    lon: float


def list_recent_history(
    db: Connection[DictRow],
    *,
    mmsi: int,
    minutes: int,
) -> list[VesselHistoryQueryRow]:
    rows = db.execute(
        """
        SELECT
            id,
            mmsi,
            ST_Y(position) AS lat,
            ST_X(position) AS lon
        FROM vessel_history
        WHERE mmsi = %s
          AND observed_at >= NOW() - make_interval(mins => %s)
        ORDER BY observed_at, id
        """,
        (mmsi, minutes),
    ).fetchall()

    return [
        VesselHistoryQueryRow(
            id=row["id"],
            mmsi=row["mmsi"],
            lat=row["lat"],
            lon=row["lon"],
        )
        for row in rows
    ]
