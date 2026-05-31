import json
from datetime import datetime
from datetime import timezone

import pytest

from app.ais_consumer import AisConsumerConfig
from app.ais_consumer import process_aisstream_message
from app.ais_consumer import run_consumer
from app.ais_consumer import upsert_live_vessel_records
from app.ais_consumer import write_source_status
from app.ais_source import AisSourceConfig
from app.cache import LIVE_AIS_STATUS_KEY
from app.cache import LIVE_VESSEL_EXPIRE_AFTER_SECONDS
from app.cache import LIVE_VESSELS_INDEX_KEY
from app.cache import deserialize_cached_live_vessel
from app.cache import live_vessel_key
from app.schemas.vessels import AisVesselRecord


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}
        self.expirations: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value
        if ex is not None:
            self.expirations[key] = ex

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
    assert (
        redis_client.expirations[live_vessel_key(123456789)]
        == LIVE_VESSEL_EXPIRE_AFTER_SECONDS
    )
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


def test_source_status_preserves_success_and_error_timing() -> None:
    redis_client = FakeRedisClient()
    ais_config = AisSourceConfig(source="aisstream")

    write_source_status(
        redis_client,
        status="connected",
        ais_config=ais_config,
        last_successful_message_at=datetime(2026, 5, 13, 16, 1, tzinfo=timezone.utc),
        last_renderable_message_at=datetime(2026, 5, 13, 16, 1, 30, tzinfo=timezone.utc),
        observed_at=datetime(2026, 5, 13, 16, 2, tzinfo=timezone.utc),
    )
    write_source_status(
        redis_client,
        status="reconnecting",
        ais_config=ais_config,
        error_message="connection closed",
        observed_at=datetime(2026, 5, 13, 16, 3, tzinfo=timezone.utc),
    )

    status = json.loads(redis_client.values[LIVE_AIS_STATUS_KEY])
    assert status == {
        "source": "aisstream",
        "status": "reconnecting",
        "updatedAt": "2026-05-13T16:03:00+00:00",
        "lastSuccessfulMessageAt": "2026-05-13T16:01:00+00:00",
        "lastRenderableMessageAt": "2026-05-13T16:01:30+00:00",
        "lastErrorAt": "2026-05-13T16:03:00+00:00",
        "lastError": "connection closed",
    }


@pytest.mark.asyncio
async def test_aisstream_consumer_reconnects_after_websocket_failure() -> None:
    redis_client = FakeRedisClient()
    connector = ReconnectingWebSocketConnector(
        [
            FailingWebSocket(RuntimeError("temporary disconnect")),
            FakeWebSocket(
                [
                    {
                        "MessageType": "PositionReport",
                        "MetaData": {
                            "MMSI": 123456789,
                            "ShipName": "TEST VESSEL",
                            "latitude": 40.1,
                            "longitude": -73.9,
                            "time_utc": "2026-05-13 16:01:00.000000 +0000 UTC",
                        },
                        "Message": {"PositionReport": {"Sog": 4.2}},
                    }
                ]
            ),
        ]
    )

    exit_code = await run_consumer(
        consumer_config=AisConsumerConfig(run_once=True, reconnect_backoff_seconds=0.1),
        ais_config=AisSourceConfig(
            source="aisstream",
            allow_fixture_fallback=False,
            aisstream_api_key="test-key",
            aisstream_ws_url="wss://example.test/stream",
            aisstream_connect_timeout_seconds=0.5,
        ),
        redis_client=redis_client,
        ws_connect=connector,
    )

    assert exit_code == 0
    assert connector.call_count == 2
    assert live_vessel_key(123456789) in redis_client.values
    status = json.loads(redis_client.values[LIVE_AIS_STATUS_KEY])
    assert status["status"] == "connected"
    assert status["lastSuccessfulMessageAt"] is not None
    assert status["lastRenderableMessageAt"] is not None
    assert status["lastErrorAt"] is not None
    assert status["lastError"] == "temporary disconnect"


class ReconnectingWebSocketConnector:
    def __init__(self, websockets: list[object]) -> None:
        self.websockets = websockets
        self.call_count = 0

    def __call__(self, url: str, open_timeout: float, **kwargs: object) -> object:
        self.call_count += 1
        websocket = self.websockets.pop(0)
        websocket.url = url
        websocket.open_timeout = open_timeout
        return websocket


class FakeWebSocket:
    def __init__(self, messages: list[object]) -> None:
        self.messages = messages
        self.sent_messages: list[str] = []
        self.url: str | None = None
        self.open_timeout: float | None = None

    async def __aenter__(self) -> "FakeWebSocket":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def send(self, message: str) -> None:
        self.sent_messages.append(message)

    async def recv(self) -> str:
        return json.dumps(self.messages.pop(0))


class FailingWebSocket:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.url: str | None = None
        self.open_timeout: float | None = None
        self.sent_messages: list[str] = []

    async def __aenter__(self) -> "FailingWebSocket":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def send(self, message: str) -> None:
        self.sent_messages.append(message)

    async def recv(self) -> str:
        raise self.error
