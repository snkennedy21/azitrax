from datetime import datetime
from datetime import timezone

from psycopg import Connection
from psycopg.rows import DictRow

from app.schemas.vessels import AisVesselRecord


def insert_vessel_history_record(
    db: Connection[DictRow],
    record: AisVesselRecord,
) -> None:
    received_at = datetime.now(timezone.utc)
    observed_at = _parse_source_timestamp(record.time_utc) or received_at

    db.execute(
        """
        INSERT INTO vessel_history (
            mmsi,
            observed_at,
            received_at,
            position
        )
        VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
        """,
        (
            record.mmsi,
            observed_at,
            received_at,
            record.lon,
            record.lat,
        ),
    )


def _parse_source_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None

    try:
        parsed = datetime.fromisoformat(value.removesuffix(" UTC"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)
