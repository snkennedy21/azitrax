from datetime import datetime
from datetime import timezone
from typing import Any

from app.cache.redis import deserialize_cached_live_vessel
from app.cache.redis import LIVE_VESSEL_EXPIRE_AFTER_SECONDS
from app.cache.redis import LIVE_VESSELS_INDEX_KEY
from app.cache.redis import live_vessel_key
from app.cache.redis import serialize_cached_live_vessel
from app.schemas.vessels import AisVesselRecord
from app.schemas.vessels import CachedLiveVessel


def upsert_live_vessel_records(
    redis_client: Any,
    records: list[AisVesselRecord],
    observed_at: datetime | None = None,
) -> int:
    written_count = 0
    observed_at = observed_at or datetime.now(timezone.utc)

    for record in records:
        vessel = build_cached_live_vessel(redis_client, record, observed_at)
        if vessel is None:
            continue

        redis_client.set(
            live_vessel_key(vessel.mmsi),
            serialize_cached_live_vessel(vessel),
            ex=LIVE_VESSEL_EXPIRE_AFTER_SECONDS,
        )
        redis_client.sadd(LIVE_VESSELS_INDEX_KEY, vessel.mmsi)
        written_count += 1

    return written_count


def build_cached_live_vessel(
    redis_client: Any,
    record: AisVesselRecord,
    observed_at: datetime,
) -> CachedLiveVessel | None:
    try:
        existing_payload = redis_client.get(live_vessel_key(record.mmsi))
    except AttributeError:
        existing_payload = None

    observed_at_value = observed_at.isoformat()
    first_seen_at = observed_at_value
    if existing_payload:
        try:
            first_seen_at = deserialize_cached_live_vessel(existing_payload).first_seen_at
        except ValueError:
            first_seen_at = observed_at_value

    try:
        return CachedLiveVessel(
            id=f"mmsi:{record.mmsi}",
            mmsi=record.mmsi,
            lat=record.lat,
            lon=record.lon,
            timestamp=record.time_utc,
            label=record.ship_name,
            course=record.cog,
            heading=record.true_heading,
            speed=record.sog,
            destination=None,
            first_seen_at=first_seen_at,
            last_seen_at=observed_at_value,
            last_message_at=_normalize_source_timestamp(record.time_utc, observed_at_value),
        )
    except ValueError:
        return None


def _normalize_source_timestamp(value: str | None, fallback: str) -> str:
    if not value:
        return fallback

    try:
        return datetime.fromisoformat(value).isoformat()
    except ValueError:
        pass

    try:
        return datetime.strptime(
            value.removesuffix(" UTC"),
            "%Y-%m-%d %H:%M:%S.%f %z",
        ).isoformat()
    except ValueError:
        return fallback
