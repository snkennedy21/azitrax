from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any

from pydantic import ValidationError

from app.ais.source import DEFAULT_BOUNDING_BOXES
from app.ais.consumer import read_source_status
from app.cache.redis import deserialize_cached_live_vessel
from app.cache.redis import LIVE_VESSEL_STALE_AFTER_SECONDS
from app.cache.redis import LIVE_VESSELS_INDEX_KEY
from app.cache.redis import live_vessel_key
from app.config import AisSourceConfig
from app.schemas.vessels import CachedLiveVessel
from app.schemas.vessels import LiveVesselMapItem
from app.schemas.vessels import LiveVesselsMetadata
from app.schemas.vessels import LiveVesselsResponse


def build_live_vessels_response(redis_client: Any) -> LiveVesselsResponse:
    fetched_at = datetime.now(timezone.utc)
    source_status = read_source_status(redis_client)
    source, bounding_boxes = _live_snapshot_config(source_status)
    raw_ids = redis_client.smembers(LIVE_VESSELS_INDEX_KEY)
    vessel_ids = _normalize_vessel_ids(raw_ids)
    cached_vessels = _load_cached_live_vessels(redis_client, vessel_ids)

    items = [_cached_vessel_to_map_item(vessel, fetched_at) for vessel in cached_vessels]
    return LiveVesselsResponse(
        items=items,
        metadata=LiveVesselsMetadata(
            source=source,
            fetched_at=fetched_at.isoformat(),
            known_count=len(vessel_ids),
            returned_count=len(items),
            last_message_at=_max_timestamp(vessel.last_message_at for vessel in cached_vessels),
            oldest_last_seen_at=_min_timestamp(vessel.last_seen_at for vessel in cached_vessels),
            source_status=source_status or {"source": source, "status": "warming"},
            bounding_boxes=bounding_boxes,
        ),
    )


def _normalize_vessel_ids(raw_ids: set[Any]) -> list[int]:
    vessel_ids: list[int] = []
    for raw_id in raw_ids:
        try:
            vessel_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue

    return sorted(vessel_ids)


def _load_cached_live_vessels(
    redis_client: Any,
    vessel_ids: list[int],
) -> list[CachedLiveVessel]:
    if not vessel_ids:
        return []

    keys = [live_vessel_key(vessel_id) for vessel_id in vessel_ids]
    if hasattr(redis_client, "mget"):
        payloads = redis_client.mget(keys)
    else:
        payloads = [redis_client.get(key) for key in keys]

    vessels: list[CachedLiveVessel] = []
    stale_index_ids: list[int] = []
    for vessel_id, payload in zip(vessel_ids, payloads, strict=True):
        if not payload:
            stale_index_ids.append(vessel_id)
            continue

        try:
            vessel = deserialize_cached_live_vessel(payload)
        except (TypeError, ValueError, ValidationError):
            stale_index_ids.append(vessel_id)
            continue

        vessels.append(vessel)

    _remove_stale_index_ids(redis_client, stale_index_ids)
    return vessels


def _cached_vessel_to_map_item(vessel: CachedLiveVessel, fetched_at: datetime) -> LiveVesselMapItem:
    return LiveVesselMapItem(
        id=vessel.id,
        lat=vessel.lat,
        lon=vessel.lon,
        timestamp=vessel.timestamp,
        last_seen_at=vessel.last_seen_at,
        freshness=_vessel_freshness(vessel, fetched_at),
        mmsi=vessel.mmsi,
        label=vessel.label,
        course=vessel.course,
        heading=vessel.heading,
        speed=vessel.speed,
        destination=vessel.destination,
    )


def _live_snapshot_config(source_status: dict[str, Any]) -> tuple[str, list[Any]]:
    try:
        config = AisSourceConfig.from_env()
    except (ValueError, RuntimeError):
        status_source = source_status.get("source")
        return (status_source if isinstance(status_source, str) else "unknown", DEFAULT_BOUNDING_BOXES)

    status_source = source_status.get("source")
    source = status_source if isinstance(status_source, str) else config.source
    return source, config.aisstream_bounding_boxes or DEFAULT_BOUNDING_BOXES


def _max_timestamp(values: Any) -> str | None:
    timestamps = [value for value in values if isinstance(value, str)]
    return max(timestamps) if timestamps else None


def _min_timestamp(values: Any) -> str | None:
    timestamps = [value for value in values if isinstance(value, str)]
    return min(timestamps) if timestamps else None


def _vessel_freshness(vessel: CachedLiveVessel, fetched_at: datetime) -> str:
    last_seen_at = _parse_utc_timestamp(vessel.last_seen_at)
    if last_seen_at is None:
        return "stale"

    stale_after = timedelta(seconds=LIVE_VESSEL_STALE_AFTER_SECONDS)
    return "stale" if fetched_at - last_seen_at >= stale_after else "fresh"


def _parse_utc_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _remove_stale_index_ids(redis_client: Any, vessel_ids: list[int]) -> None:
    if not vessel_ids or not hasattr(redis_client, "srem"):
        return

    redis_client.srem(LIVE_VESSELS_INDEX_KEY, *vessel_ids)
