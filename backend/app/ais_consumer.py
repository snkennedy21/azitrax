from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
import json
import os
import signal
import ssl
from typing import Any

from app.ais_source import AisSourceConfig
from app.ais_source import AisSourceError
from app.ais_source import DEFAULT_BOUNDING_BOXES
from app.ais_source import load_ais_vessel_records
from app.cache import create_redis_client
from app.cache import deserialize_cached_live_vessel
from app.cache import LIVE_AIS_STATUS_KEY
from app.cache import LIVE_VESSELS_INDEX_KEY
from app.cache import live_vessel_key
from app.cache import serialize_cached_live_vessel
from app.schemas import AisVesselRecord
from app.schemas import CachedLiveVessel


@dataclass(frozen=True)
class AisConsumerConfig:
    poll_seconds: float = 60.0
    run_once: bool = False
    reconnect_backoff_seconds: float = 5.0

    @classmethod
    def from_env(cls) -> AisConsumerConfig:
        return cls(
            poll_seconds=max(0.1, float(os.getenv("AIS_CONSUMER_POLL_SECONDS", "60"))),
            run_once=_parse_bool(os.getenv("AIS_CONSUMER_RUN_ONCE", "false")),
            reconnect_backoff_seconds=max(
                0.1,
                float(os.getenv("AIS_CONSUMER_RECONNECT_BACKOFF_SECONDS", "5")),
            ),
        )


async def run_consumer(
    consumer_config: AisConsumerConfig | None = None,
    ais_config: AisSourceConfig | None = None,
    stop_event: asyncio.Event | None = None,
    redis_client: Any | None = None,
    ws_connect: Any | None = None,
) -> int:
    try:
        consumer_config = consumer_config or AisConsumerConfig.from_env()
        ais_config = ais_config or AisSourceConfig.from_env()
    except (AisSourceError, ValueError):
        return 1

    stop_event = stop_event or asyncio.Event()
    owns_redis_client = redis_client is None
    redis_client = redis_client or create_redis_client()

    exit_code = 0
    try:
        if ais_config.source == "aisstream":
            return await _consume_aisstream(
                redis_client=redis_client,
                consumer_config=consumer_config,
                ais_config=ais_config,
                stop_event=stop_event,
                ws_connect=ws_connect,
            )

        while not stop_event.is_set():
            try:
                records = await load_ais_vessel_records(ais_config)
            except AisSourceError:
                exit_code = 1
                break

            upsert_live_vessel_records(redis_client, records)

            if consumer_config.run_once:
                break

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=consumer_config.poll_seconds)
            except TimeoutError:
                continue
    finally:
        if owns_redis_client:
            redis_client.close()

    return exit_code


async def _consume_aisstream(
    redis_client: Any,
    consumer_config: AisConsumerConfig,
    ais_config: AisSourceConfig,
    stop_event: asyncio.Event,
    ws_connect: Any | None = None,
) -> int:
    if not ais_config.aisstream_api_key:
        write_source_status(
            redis_client,
            status="unavailable",
            ais_config=ais_config,
            error_message="AISSTREAM_API_KEY is required for AIS_SOURCE=aisstream",
        )
        return 1

    subscription = {
        "APIKey": ais_config.aisstream_api_key,
        "BoundingBoxes": ais_config.aisstream_bounding_boxes or DEFAULT_BOUNDING_BOXES,
        "FilterMessageTypes": ais_config.aisstream_message_types or ["PositionReport"],
    }

    connect = ws_connect or _default_ws_connect
    connect_kwargs: dict[str, Any] = {"open_timeout": ais_config.aisstream_connect_timeout_seconds}
    if ais_config.aisstream_disable_tls_verify:
        connect_kwargs["ssl"] = ssl._create_unverified_context()

    write_source_status(redis_client, status="connecting", ais_config=ais_config)
    while not stop_event.is_set():
        try:
            async with connect(ais_config.aisstream_ws_url, **connect_kwargs) as websocket:
                await websocket.send(json.dumps(subscription))
                write_source_status(redis_client, status="connected", ais_config=ais_config)

                while not stop_event.is_set():
                    raw_message = await websocket.recv()
                    try:
                        source_message = json.loads(raw_message)
                    except json.JSONDecodeError as exc:
                        write_source_status(
                            redis_client,
                            status="degraded",
                            ais_config=ais_config,
                            error_message=str(exc),
                        )
                        continue

                    write_source_status(
                        redis_client,
                        status="connected",
                        ais_config=ais_config,
                        last_successful_message_at=datetime.now(timezone.utc),
                    )
                    written_count = process_aisstream_message(redis_client, source_message)
                    if written_count:
                        write_source_status(
                            redis_client,
                            status="connected",
                            ais_config=ais_config,
                            last_renderable_message_at=datetime.now(timezone.utc),
                        )
                    if consumer_config.run_once and written_count:
                        return 0
        except Exception as exc:
            if stop_event.is_set():
                break

            write_source_status(
                redis_client,
                status="reconnecting",
                ais_config=ais_config,
                error_message=str(exc),
            )
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=consumer_config.reconnect_backoff_seconds,
                )
            except TimeoutError:
                continue

    return 0


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

        redis_client.set(live_vessel_key(vessel.mmsi), serialize_cached_live_vessel(vessel))
        redis_client.sadd(LIVE_VESSELS_INDEX_KEY, vessel.mmsi)
        written_count += 1

    return written_count


def process_aisstream_message(
    redis_client: Any,
    message: Any,
    observed_at: datetime | None = None,
) -> int:
    record = normalize_aisstream_message(message)
    if record is None:
        return 0

    return upsert_live_vessel_records(redis_client, [record], observed_at=observed_at)


def write_source_status(
    redis_client: Any,
    status: str,
    ais_config: AisSourceConfig,
    error_message: str | None = None,
    last_successful_message_at: datetime | None = None,
    last_renderable_message_at: datetime | None = None,
    observed_at: datetime | None = None,
) -> None:
    observed_at = observed_at or datetime.now(timezone.utc)
    previous_status = read_source_status(redis_client)

    payload = {
        "source": ais_config.source,
        "status": status,
        "updatedAt": observed_at.isoformat(),
        "lastSuccessfulMessageAt": _preserved_timestamp(
            previous_status,
            "lastSuccessfulMessageAt",
            last_successful_message_at,
        ),
        "lastRenderableMessageAt": _preserved_timestamp(
            previous_status,
            "lastRenderableMessageAt",
            last_renderable_message_at,
        ),
        "lastErrorAt": previous_status.get("lastErrorAt"),
        "lastError": previous_status.get("lastError"),
    }

    if error_message:
        payload["lastErrorAt"] = observed_at.isoformat()
        payload["lastError"] = error_message

    redis_client.set(LIVE_AIS_STATUS_KEY, json.dumps(payload))


def read_source_status(redis_client: Any) -> dict[str, Any]:
    try:
        payload = redis_client.get(LIVE_AIS_STATUS_KEY)
    except AttributeError:
        return {}

    if not payload:
        return {}

    try:
        decoded = json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        return {}

    return decoded if isinstance(decoded, dict) else {}


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


def normalize_aisstream_message(message: Any) -> AisVesselRecord | None:
    if not isinstance(message, dict) or message.get("MessageType") != "PositionReport":
        return None

    metadata = message.get("MetaData") or {}
    message_payload = message.get("Message") or {}
    if not isinstance(metadata, dict) or not isinstance(message_payload, dict):
        return None

    position_report = message_payload.get("PositionReport") or {}
    if not isinstance(position_report, dict):
        return None

    lat = metadata.get("latitude", position_report.get("Latitude"))
    lon = metadata.get("longitude", position_report.get("Longitude"))
    mmsi = metadata.get("MMSI", position_report.get("UserID"))
    if lat is None or lon is None or mmsi is None:
        return None

    try:
        return AisVesselRecord(
            mmsi=int(mmsi),
            ship_name=_clean_ship_name(metadata.get("ShipName")),
            lat=float(lat),
            lon=float(lon),
            time_utc=metadata.get("time_utc"),
            sog=_optional_float(position_report.get("Sog")),
            cog=_optional_float(position_report.get("Cog")),
            true_heading=_optional_int(position_report.get("TrueHeading")),
            navigational_status=_optional_int(position_report.get("NavigationalStatus")),
            position_accuracy=position_report.get("PositionAccuracy"),
        )
    except (TypeError, ValueError):
        return None


def _default_ws_connect(url: str, open_timeout: float, **kwargs: Any) -> Any:
    try:
        import websockets
    except ImportError as exc:
        raise AisSourceError("websockets is required for AIS_SOURCE=aisstream") from exc

    return websockets.connect(url, open_timeout=open_timeout, **kwargs)


def _normalize_source_timestamp(value: str | None, fallback: str) -> str:
    if not value:
        return fallback

    try:
        return datetime.fromisoformat(value).isoformat()
    except ValueError:
        pass

    try:
        return datetime.strptime(value.removesuffix(" UTC"), "%Y-%m-%d %H:%M:%S.%f %z").isoformat()
    except ValueError:
        return fallback


def _preserved_timestamp(
    previous_status: dict[str, Any],
    key: str,
    value: datetime | None,
) -> str | None:
    if value is not None:
        return value.isoformat()

    previous_value = previous_status.get(key)
    return previous_value if isinstance(previous_value, str) else None


def _clean_ship_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def main() -> int:
    async def _main() -> int:

        ## Clean Shutdown writes (Ctrl+C/Docker stop signals)
        stop_event = asyncio.Event()
        _install_signal_handlers(stop_event)

        # Actual Consumer
        return await run_consumer(stop_event=stop_event)

    try:
        return asyncio.run(_main())
    except KeyboardInterrupt:
        return 0


def _install_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stop_event.set)
        except NotImplementedError:
            signal.signal(signal_name, lambda *_: stop_event.set())


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
