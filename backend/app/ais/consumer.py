from __future__ import annotations

import asyncio
from datetime import datetime
from datetime import timezone
import json
import signal
import ssl
import sys
from typing import Any

from psycopg import Connection
from psycopg import Error as PsycopgError
from psycopg.rows import DictRow
from psycopg_pool import ConnectionPool
from psycopg_pool import PoolTimeout
from redis.exceptions import RedisError

from app.ais.source import AisSourceError
from app.ais.source import DEFAULT_BOUNDING_BOXES
from app.ais.source import load_ais_vessel_records
from app.config import AisConsumerConfig
from app.config import AisSourceConfig
from app.db.connection import create_pool
from app.cache.redis import create_redis_client
from app.projections.live_vessels import upsert_live_vessel_records
from app.projections.source_status import consumer_health_check
from app.projections.source_status import write_source_status
from app.repositories.vessel_history import insert_vessel_history_record
from app.schemas.vessels import AisVesselRecord


class ConsumerDatabaseError(RuntimeError):
    """A database failure while processing a provider message."""


async def run_consumer(
    consumer_config: AisConsumerConfig | None = None,
    ais_config: AisSourceConfig | None = None,
    stop_event: asyncio.Event | None = None,
    redis_client: Any | None = None,
    ws_connect: Any | None = None,
    db_pool: ConnectionPool | None = None,
) -> int:
    try:
        consumer_config = consumer_config or AisConsumerConfig.from_env()
        ais_config = ais_config or AisSourceConfig.from_env()
    except (AisSourceError, ValueError):
        return 1

    stop_event = stop_event or asyncio.Event()
    owns_redis_client = redis_client is None
    redis_client = redis_client or create_redis_client()
    owns_db_pool = db_pool is None
    db_pool = db_pool or create_pool()

    exit_code = 0
    try:
        if owns_db_pool:
            try:
                db_pool.open()
            except (PsycopgError, PoolTimeout, OSError) as exc:
                write_source_status(
                    redis_client,
                    status="database_unavailable",
                    ais_config=ais_config,
                    error_message=str(exc),
                )
                return 1

        if ais_config.source == "aisstream":
            return await _consume_aisstream(
                redis_client=redis_client,
                consumer_config=consumer_config,
                ais_config=ais_config,
                stop_event=stop_event,
                ws_connect=ws_connect,
                db_pool=db_pool,
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
        if owns_db_pool:
            db_pool.close()

    return exit_code


async def _consume_aisstream(
    redis_client: Any,
    consumer_config: AisConsumerConfig,
    ais_config: AisSourceConfig,
    stop_event: asyncio.Event,
    ws_connect: Any | None = None,
    db_pool: ConnectionPool | None = None,
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

    # Try connecting to aisstream continuously
    while not stop_event.is_set():
        try:
            async with connect(ais_config.aisstream_ws_url, **connect_kwargs) as websocket:
                await websocket.send(json.dumps(subscription))
                write_source_status(redis_client, status="connected", ais_config=ais_config)

                # Pull in data from aisstream continuously
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

                    if db_pool is None:
                        raise RuntimeError("database pool is required for AISStream consumption")

                    try:
                        with db_pool.connection() as db:
                            written_count = process_aisstream_message(
                                redis_client,
                                source_message,
                                db=db,
                            )
                    except (PsycopgError, PoolTimeout) as exc:
                        raise ConsumerDatabaseError(str(exc)) from exc

                    if written_count:
                        write_source_status(
                            redis_client,
                            status="connected",
                            ais_config=ais_config,
                            last_successful_message_at=datetime.now(timezone.utc),
                            last_renderable_message_at=datetime.now(timezone.utc),
                        )
                    if consumer_config.run_once and written_count:
                        return 0
        except ConsumerDatabaseError as exc:
            if stop_event.is_set():
                break

            write_source_status(
                redis_client,
                status="database_unavailable",
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
        except RedisError as exc:
            if stop_event.is_set():
                break

            # Redis is a sink dependency, not an AIS transport failure.
            # Status cannot be written when Redis is unavailable, so the
            # health probe will fail its ping check.
            print(f"Redis sink unavailable: {exc}")
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=consumer_config.reconnect_backoff_seconds,
                )
            except TimeoutError:
                continue
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


def process_aisstream_message(
    redis_client: Any,
    message: Any,
    db: Connection[DictRow],
    observed_at: datetime | None = None,
) -> int:
    record = normalize_aisstream_message(message)
    if record is None:
        return 0

    insert_vessel_history_record(db, record)

    return upsert_live_vessel_records(redis_client, [record], observed_at=observed_at)


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
    if len(sys.argv) == 2 and sys.argv[1] == "--health":
        try:
            config = AisConsumerConfig.from_env()
            client = create_redis_client()
            try:
                consumer_health_check(client, config.health_max_age_seconds)
            finally:
                client.close()
        except (RedisError, RuntimeError, ValueError) as exc:
            print(f"Consumer health check failed: {exc}")
            return 1
        return 0

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


if __name__ == "__main__":
    raise SystemExit(main())
