from datetime import datetime
from datetime import timezone

import pytest
from psycopg import Connection

from app.schemas.vessels import AisVesselRecord
from app.services.vessel_history import insert_vessel_history_record


def test_insert_vessel_history_record_persists_position_observation(
    db_connection: Connection,
) -> None:
    record = AisVesselRecord(
        mmsi=636020226,
        ship_name="SEABOARD EXPLORER",
        lat=40.68517,
        lon=-74.01049,
        time_utc="2026-10-14 19:37:03.822676892 +0000 UTC",
        sog=0.0,
        cog=115.1,
        true_heading=52,
        navigational_status=5,
        position_accuracy=False,
    )
    received_after = datetime.now(timezone.utc)

    try:
        insert_vessel_history_record(db_connection, record)

        row = db_connection.execute(
            """
            SELECT
                mmsi,
                observed_at,
                received_at,
                ST_Y(position) AS lat,
                ST_X(position) AS lon
            FROM vessel_history
            WHERE mmsi = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (record.mmsi,),
        ).fetchone()

        assert row is not None
        assert row["mmsi"] == record.mmsi
        assert row["observed_at"] == datetime(
            2026,
            10,
            14,
            19,
            37,
            3,
            822676,
            tzinfo=timezone.utc,
        )
        assert received_after <= row["received_at"] <= datetime.now(timezone.utc)
        assert row["lat"] == pytest.approx(record.lat)
        assert row["lon"] == pytest.approx(record.lon)
    finally:
        db_connection.rollback()
