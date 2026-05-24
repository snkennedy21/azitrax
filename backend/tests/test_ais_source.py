import json
from pathlib import Path

import pytest

from app.ais_source import AisSourceClient
from app.ais_source import AisSourceConfig
from app.ais_source import map_live_vessel_items
from app.schemas import AisVesselRecord


def fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "app/fixtures/aisstream-position-reports-sample.json"


@pytest.mark.asyncio
async def test_loads_vessel_records_from_fixture_without_network() -> None:
    config = AisSourceConfig(
        source="fixture",
        fixture_path=fixture_path(),
        aisstream_sample_message_limit=2,
    )

    records = await AisSourceClient(config).load_vessel_records()

    assert len(records) == 2
    assert records[0].mmsi == 367123456
    assert records[0].ship_name == "HARBOR PILOT"
    assert records[0].lat == pytest.approx(40.67472)
    assert records[0].lon == pytest.approx(-74.04514)
    assert records[0].sog == pytest.approx(8.7)


@pytest.mark.asyncio
async def test_loads_successful_aisstream_response_with_timeout_and_limit() -> None:
    websocket = FakeWebSocket(
        [
            {
                "MessageType": "PositionReport",
                "MetaData": {
                    "MMSI": 123456789,
                    "ShipName": " TEST VESSEL ",
                    "latitude": 40.1,
                    "longitude": -73.9,
                    "time_utc": "2026-05-13 16:01:00.000000 +0000 UTC",
                },
                "Message": {
                    "PositionReport": {
                        "Sog": 4.2,
                        "Cog": 91.5,
                        "TrueHeading": 92,
                        "NavigationalStatus": 0,
                        "PositionAccuracy": True,
                    }
                },
            },
            {
                "MessageType": "PositionReport",
                "MetaData": {
                    "MMSI": 987654321,
                    "latitude": 40.2,
                    "longitude": -74.0,
                },
                "Message": {"PositionReport": {}},
            },
        ]
    )

    config = AisSourceConfig(
        source="aisstream",
        allow_fixture_fallback=False,
        aisstream_api_key="test-key",
        aisstream_ws_url="wss://example.test/stream",
        aisstream_bounding_boxes=[[[1, 2], [3, 4]]],
        aisstream_message_types=["PositionReport"],
        aisstream_connect_timeout_seconds=0.5,
        aisstream_sample_message_limit=1,
    )

    def connect(url, open_timeout):
        websocket.url = url
        websocket.open_timeout = open_timeout
        return websocket

    client = AisSourceClient(config, ws_connect=connect)

    records = await client.load_vessel_records()

    assert len(records) == 1
    assert records[0].mmsi == 123456789
    assert records[0].ship_name == "TEST VESSEL"
    assert records[0].lat == pytest.approx(40.1)
    assert records[0].lon == pytest.approx(-73.9)
    assert websocket.url == "wss://example.test/stream"
    assert websocket.open_timeout == 0.5

    subscription = json.loads(websocket.sent_messages[0])
    assert subscription == {
        "APIKey": "test-key",
        "BoundingBoxes": [[[1, 2], [3, 4]]],
        "FilterMessageTypes": ["PositionReport"],
    }


def test_maps_complete_vessel_record_to_live_map_item() -> None:
    record = AisVesselRecord(
        mmsi=123456789,
        ship_name="TEST VESSEL",
        lat=40.1,
        lon=-73.9,
        time_utc="2026-05-13 16:01:00.000000 +0000 UTC",
        sog=4.2,
        cog=91.5,
        true_heading=92,
    )

    items = map_live_vessel_items([record])

    assert len(items) == 1
    assert items[0].id == "mmsi:123456789"
    assert items[0].lat == pytest.approx(40.1)
    assert items[0].lon == pytest.approx(-73.9)
    assert items[0].timestamp == "2026-05-13 16:01:00.000000 +0000 UTC"
    assert items[0].mmsi == 123456789
    assert items[0].label == "TEST VESSEL"
    assert items[0].speed == pytest.approx(4.2)
    assert items[0].course == pytest.approx(91.5)
    assert items[0].heading == 92


def test_skips_vessel_record_without_valid_coordinates() -> None:
    record = AisVesselRecord.model_construct(
        mmsi=123456789,
        ship_name="MALFORMED",
        lat=None,
        lon=-73.9,
        time_utc="2026-05-13 16:01:00.000000 +0000 UTC",
    )

    assert map_live_vessel_items([record]) == []


class FakeWebSocket:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent_messages = []
        self.url = None
        self.open_timeout = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def send(self, message):
        self.sent_messages.append(message)

    async def recv(self):
        return json.dumps(self.messages.pop(0))
