import json

import pytest
from pydantic import ValidationError

from app.cache import LIVE_VESSELS_INDEX_KEY
from app.cache import deserialize_cached_live_vessel
from app.cache import live_vessel_key
from app.cache import serialize_cached_live_vessel
from app.schemas import CachedLiveVessel


def valid_cached_vessel_payload() -> dict[str, object]:
    return {
        "id": "mmsi:123456789",
        "mmsi": 123456789,
        "lat": 40.1,
        "lon": -73.9,
        "timestamp": "2026-05-13 16:01:00.000000 +0000 UTC",
        "label": "TEST VESSEL",
        "course": 91.5,
        "heading": 92,
        "speed": 4.2,
        "destination": None,
        "firstSeenAt": "2026-05-13T16:00:00+00:00",
        "lastSeenAt": "2026-05-13T16:02:00+00:00",
        "lastMessageAt": "2026-05-13T16:01:00+00:00",
    }


def test_live_vessel_cache_keys_are_documented_contract() -> None:
    assert live_vessel_key(123456789) == "vessel:123456789"
    assert LIVE_VESSELS_INDEX_KEY == "live:vessels"


def test_valid_cached_vessel_payload_round_trips_as_normalized_json() -> None:
    vessel = CachedLiveVessel.model_validate(valid_cached_vessel_payload())

    serialized = serialize_cached_live_vessel(vessel)
    raw_payload = json.loads(serialized)
    deserialized = deserialize_cached_live_vessel(serialized)

    assert raw_payload == valid_cached_vessel_payload()
    assert deserialized == vessel


def test_cached_vessel_payload_rejects_missing_coordinates() -> None:
    payload = valid_cached_vessel_payload()
    del payload["lat"]

    with pytest.raises(ValidationError):
        CachedLiveVessel.model_validate(payload)


@pytest.mark.parametrize(
    ("lat", "lon"),
    [
        (91, -73.9),
        (40.1, -181),
        ("not-a-latitude", -73.9),
    ],
)
def test_cached_vessel_payload_rejects_invalid_coordinates(lat: object, lon: object) -> None:
    payload = valid_cached_vessel_payload()
    payload["lat"] = lat
    payload["lon"] = lon

    with pytest.raises(ValidationError):
        CachedLiveVessel.model_validate(payload)
