"""Run the source-to-serving smoke test against the assembled Compose stack."""

from __future__ import annotations

import json
from pathlib import Path

from app.ais.consumer import process_aisstream_message
from app.cache.redis import create_redis_client
from app.cache.redis import deserialize_cached_live_vessel
from app.cache.redis import live_vessel_key
from app.db.connection import create_pool


FIXTURE_PATH = Path("/app/app/ais/fixtures/aisstream-position-reports-sample.json")


def main() -> None:
    messages = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    message = messages[0]
    expected_mmsi = message["Message"]["PositionReport"]["UserID"]

    db_pool = create_pool()
    redis_client = create_redis_client()
    try:
        db_pool.open()
        with db_pool.connection() as db:
            written_count = process_aisstream_message(redis_client, message, db)
            db.commit()

            history = db.execute(
                """
                SELECT mmsi
                FROM vessel_history
                WHERE mmsi = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (expected_mmsi,),
            ).fetchone()

        cached_payload = redis_client.get(live_vessel_key(expected_mmsi))
        cached_vessel = (
            deserialize_cached_live_vessel(cached_payload)
            if cached_payload is not None
            else None
        )

        if written_count != 1:
            raise RuntimeError(f"expected one processed fixture message, got {written_count}")
        if history is None or history["mmsi"] != expected_mmsi:
            raise RuntimeError("fixture message did not reach vessel_history")
        if cached_vessel is None or cached_vessel.mmsi != expected_mmsi:
            raise RuntimeError("fixture message did not reach the live Redis projection")

        print(
            f"source-to-serving smoke test passed: mmsi={expected_mmsi} "
            "reached history and live projection"
        )
    finally:
        redis_client.close()
        db_pool.close()


if __name__ == "__main__":
    main()
