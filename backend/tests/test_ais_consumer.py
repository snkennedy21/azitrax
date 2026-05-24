from datetime import datetime
from datetime import timezone

import pytest

from app.ais_consumer import process_aisstream_message
from app.ais_consumer import upsert_live_vessel_records
from app.cache import LIVE_VESSELS_INDEX_KEY
from app.cache import deserialize_cached_live_vessel
from app.cache import live_vessel_key
from app.schemas import AisVesselRecord


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def sadd(self, key: str, value: object) -> None:
        self.sets.setdefault(key, set()).add(str(value))


def test_first_live_vessel_write_updates_record_and_known_set() -> None:
    redis_client = FakeRedisClient()
    observed_at = datetime(2026, 5, 13, 16, 2, tzinfo=timezone.utc)

    written_count = upsert_live_vessel_records(
        redis_client,
        [
            AisVesselRecord(
                mmsi=123456789,
                ship_name="TEST VESSEL",
                lat=40.1,
                lon=-73.9,
                time_utc="2026-05-13 16:01:00.000000 +0000 UTC",
                sog=4.2,
                cog=91.5,
                true_heading=92,
            )
        ],
        observed_at=observed_at,
    )

    assert written_count == 1
    vessel = deserialize_cached_live_vessel(redis_client.values[live_vessel_key(123456789)])
    assert vessel.id == "mmsi:123456789"
    assert vessel.mmsi == 123456789
    assert vessel.lat == pytest.approx(40.1)
    assert vessel.lon == pytest.approx(-73.9)
    assert vessel.first_seen_at == "2026-05-13T16:02:00+00:00"
    assert vessel.last_seen_at == "2026-05-13T16:02:00+00:00"
    assert vessel.last_message_at == "2026-05-13T16:01:00+00:00"
    assert redis_client.sets[LIVE_VESSELS_INDEX_KEY] == {"123456789"}


def test_subsequent_live_vessel_write_updates_same_latest_record() -> None:
    redis_client = FakeRedisClient()
    first_seen_at = datetime(2026, 5, 13, 16, 2, tzinfo=timezone.utc)
    last_seen_at = datetime(2026, 5, 13, 16, 3, tzinfo=timezone.utc)

    upsert_live_vessel_records(
        redis_client,
        [
            AisVesselRecord(
                mmsi=123456789,
                ship_name="TEST VESSEL",
                lat=40.1,
                lon=-73.9,
                time_utc="2026-05-13 16:01:00.000000 +0000 UTC",
            )
        ],
        observed_at=first_seen_at,
    )
    upsert_live_vessel_records(
        redis_client,
        [
            AisVesselRecord(
                mmsi=123456789,
                ship_name="TEST VESSEL",
                lat=40.2,
                lon=-74.0,
                time_utc="2026-05-13 16:02:30.000000 +0000 UTC",
            )
        ],
        observed_at=last_seen_at,
    )

    assert set(redis_client.values) == {live_vessel_key(123456789)}
    vessel = deserialize_cached_live_vessel(redis_client.values[live_vessel_key(123456789)])
    assert vessel.lat == pytest.approx(40.2)
    assert vessel.lon == pytest.approx(-74.0)
    assert vessel.first_seen_at == "2026-05-13T16:02:00+00:00"
    assert vessel.last_seen_at == "2026-05-13T16:03:00+00:00"
    assert vessel.last_message_at == "2026-05-13T16:02:30+00:00"
    assert redis_client.sets[LIVE_VESSELS_INDEX_KEY] == {"123456789"}


def test_malformed_aisstream_message_is_skipped_without_redis_write() -> None:
    redis_client = FakeRedisClient()

    written_count = process_aisstream_message(
        redis_client,
        {
            "MessageType": "PositionReport",
            "MetaData": {
                "MMSI": 123456789,
                "latitude": None,
                "longitude": -73.9,
            },
            "Message": {"PositionReport": {}},
        },
        observed_at=datetime(2026, 5, 13, 16, 2, tzinfo=timezone.utc),
    )

    assert written_count == 0
    assert redis_client.values == {}
    assert redis_client.sets == {}
