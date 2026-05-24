import json
from datetime import datetime
from datetime import timezone

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.ais_consumer import upsert_live_vessel_records
from app.cache import LIVE_AIS_STATUS_KEY
from app.cache import LIVE_VESSELS_INDEX_KEY
from app.main import app
from app.schemas import AisVesselRecord


def test_live_vessels_endpoint_reads_populated_redis_snapshot(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = app.state.redis_client
    monkeypatch.setenv("AIS_SOURCE", "aisstream")
    monkeypatch.setenv("AISSTREAM_BOUNDING_BOXES", "[[[1,2],[3,4]]]")
    upsert_live_vessel_records(
        redis_client,
        [
            AisVesselRecord(
                mmsi=123456789,
                ship_name="TEST VESSEL",
                lat=40.1,
                lon=-73.9,
                time_utc="2026-05-13T16:01:00+00:00",
                sog=4.2,
                cog=91.5,
                true_heading=92,
            )
        ],
        observed_at=datetime(2026, 5, 13, 16, 2, tzinfo=timezone.utc),
    )
    redis_client.set(
        LIVE_AIS_STATUS_KEY,
        json.dumps({
            "source": "aisstream",
            "status": "connected",
            "updatedAt": "2026-05-13T16:02:00+00:00",
            "lastSuccessfulMessageAt": "2026-05-13T16:01:00+00:00",
            "lastRenderableMessageAt": "2026-05-13T16:01:00+00:00",
            "lastErrorAt": None,
            "lastError": None,
        }),
    )

    response = client.get("/live/vessels")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == [
        {
            "id": "mmsi:123456789",
            "lat": 40.1,
            "lon": -73.9,
            "timestamp": "2026-05-13T16:01:00+00:00",
            "mmsi": 123456789,
            "label": "TEST VESSEL",
            "course": 91.5,
            "heading": 92,
            "speed": 4.2,
            "destination": None,
        }
    ]
    assert payload["metadata"]["source"] == "aisstream"
    assert payload["metadata"]["knownCount"] == 1
    assert payload["metadata"]["returnedCount"] == 1
    assert payload["metadata"]["lastMessageAt"] == "2026-05-13T16:01:00+00:00"
    assert payload["metadata"]["oldestLastSeenAt"] == "2026-05-13T16:02:00+00:00"
    assert payload["metadata"]["sourceStatus"]["status"] == "connected"
    assert payload["metadata"]["boundingBoxes"] == [[[1, 2], [3, 4]]]
    assert datetime.fromisoformat(payload["metadata"]["fetchedAt"])


def test_live_vessels_endpoint_returns_empty_warming_snapshot(client: TestClient) -> None:
    response = client.get("/live/vessels")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["metadata"]["knownCount"] == 0
    assert payload["metadata"]["returnedCount"] == 0
    assert payload["metadata"]["lastMessageAt"] is None
    assert payload["metadata"]["oldestLastSeenAt"] is None
    assert payload["metadata"]["sourceStatus"]["status"] == "warming"


def test_live_vessels_endpoint_reports_source_unavailable_snapshot(client: TestClient) -> None:
    redis_client = app.state.redis_client
    redis_client.set(
        LIVE_AIS_STATUS_KEY,
        json.dumps({
            "source": "aisstream",
            "status": "unavailable",
            "updatedAt": "2026-05-13T16:02:00+00:00",
            "lastSuccessfulMessageAt": None,
            "lastRenderableMessageAt": None,
            "lastErrorAt": "2026-05-13T16:02:00+00:00",
            "lastError": "AISSTREAM_API_KEY is required for AIS_SOURCE=aisstream",
        }),
    )

    response = client.get("/live/vessels")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["metadata"]["source"] == "aisstream"
    assert payload["metadata"]["sourceStatus"]["status"] == "unavailable"
    assert payload["metadata"]["sourceStatus"]["lastError"] == (
        "AISSTREAM_API_KEY is required for AIS_SOURCE=aisstream"
    )


def test_live_vessels_endpoint_tolerates_partial_snapshot(client: TestClient) -> None:
    redis_client = app.state.redis_client
    redis_client.sadd(LIVE_VESSELS_INDEX_KEY, 123456789)

    response = client.get("/live/vessels")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["metadata"]["knownCount"] == 1
    assert payload["metadata"]["returnedCount"] == 0


def test_live_vessels_endpoint_does_not_call_live_ais_source(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_load(*args: object, **kwargs: object) -> None:
        raise AssertionError("request path must not load AIS source")

    monkeypatch.setattr("app.ais_source.load_ais_vessel_records", fail_load)
    monkeypatch.setattr("app.main.load_ais_vessel_records", fail_load, raising=False)

    response = client.get("/live/vessels")

    assert response.status_code == 200


def test_legacy_vessels_endpoint_uses_same_redis_snapshot(client: TestClient) -> None:
    response = client.get("/vessels")

    assert response.status_code == 200
    assert response.json()["metadata"]["returnedCount"] == 0


def test_live_vessels_endpoint_returns_503_when_redis_unavailable(client: TestClient) -> None:
    class UnavailableRedisClient:
        def get(self, key: str) -> None:
            return None

        def smembers(self, key: str) -> set[object]:
            raise RedisConnectionError("connection refused")

    previous_client = app.state.redis_client
    app.state.redis_client = UnavailableRedisClient()
    try:
        response = client.get("/live/vessels")
    finally:
        app.state.redis_client = previous_client

    assert response.status_code == 503
    assert response.json() == {"detail": "redis unavailable"}
