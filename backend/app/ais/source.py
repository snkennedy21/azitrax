from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
import ssl
from typing import Any

from app.config import AisSourceConfig
from app.config import DEFAULT_AIS_BOUNDING_BOXES
from app.schemas.vessels import AisVesselRecord
from app.schemas.vessels import LiveVesselMapItem


DEFAULT_BOUNDING_BOXES = DEFAULT_AIS_BOUNDING_BOXES


class AisSourceError(RuntimeError):
    """Raised when the configured AIS source cannot provide records."""


class AisSourceClient:
    def __init__(
        self,
        config: AisSourceConfig | None = None,
        ws_connect: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config or AisSourceConfig.from_env()
        self._ws_connect = ws_connect or _default_ws_connect

    async def load_vessel_records(self) -> list[AisVesselRecord]:
        if self.config.source == "fixture":
            return self._load_fixture_records()

        if self.config.source != "aisstream":
            raise AisSourceError(f"unsupported AIS_SOURCE: {self.config.source}")

        try:
            return await self._load_aisstream_records()
        except Exception as exc:
            if self.config.allow_fixture_fallback:
                return self._load_fixture_records()
            if isinstance(exc, AisSourceError):
                raise
            raise AisSourceError("AISStream source failed") from exc

    def _load_fixture_records(self) -> list[AisVesselRecord]:
        try:
            payload = json.loads(self.config.fixture_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise AisSourceError(f"AIS fixture could not be read: {self.config.fixture_path}") from exc
        except json.JSONDecodeError as exc:
            raise AisSourceError(f"AIS fixture is not valid JSON: {self.config.fixture_path}") from exc

        messages = payload if isinstance(payload, list) else [payload]
        return self._records_from_messages(messages)[: self.config.aisstream_sample_message_limit]

    async def _load_aisstream_records(self) -> list[AisVesselRecord]:
        if not self.config.aisstream_api_key:
            raise AisSourceError("AISSTREAM_API_KEY is required for AIS_SOURCE=aisstream")

        subscription = {
            "APIKey": self.config.aisstream_api_key,
            "BoundingBoxes": self.config.aisstream_bounding_boxes or DEFAULT_BOUNDING_BOXES,
            "FilterMessageTypes": self.config.aisstream_message_types or ["PositionReport"],
        }

        records: list[AisVesselRecord] = []
        timeout = self.config.aisstream_connect_timeout_seconds
        connect_kwargs: dict[str, Any] = {"open_timeout": timeout}
        if self.config.aisstream_disable_tls_verify:
            connect_kwargs["ssl"] = ssl._create_unverified_context()

        async with asyncio.timeout(timeout):
            async with self._ws_connect(self.config.aisstream_ws_url, **connect_kwargs) as websocket:
                await websocket.send(json.dumps(subscription))

                while len(records) < self.config.aisstream_sample_message_limit:
                    raw_message = await websocket.recv()
                    source_message = json.loads(raw_message)
                    if _looks_like_source_error(source_message):
                        raise AisSourceError(f"AISStream returned an error: {source_message}")
                    records.extend(self._records_from_messages([source_message]))

        return records[: self.config.aisstream_sample_message_limit]

    def _records_from_messages(self, messages: list[Any]) -> list[AisVesselRecord]:
        records: list[AisVesselRecord] = []

        for message in messages:
            if not isinstance(message, dict) or message.get("MessageType") != "PositionReport":
                continue

            metadata = message.get("MetaData") or {}
            position_report = (message.get("Message") or {}).get("PositionReport") or {}
            if not isinstance(metadata, dict) or not isinstance(position_report, dict):
                continue

            lat = metadata.get("latitude", position_report.get("Latitude"))
            lon = metadata.get("longitude", position_report.get("Longitude"))
            mmsi = metadata.get("MMSI", position_report.get("UserID"))
            if lat is None or lon is None or mmsi is None:
                continue

            records.append(
                AisVesselRecord(
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
            )

        return records


async def load_ais_vessel_records(config: AisSourceConfig | None = None) -> list[AisVesselRecord]:
    return await AisSourceClient(config).load_vessel_records()


def map_live_vessel_items(records: list[AisVesselRecord]) -> list[LiveVesselMapItem]:
    items: list[LiveVesselMapItem] = []

    for record in records:
        if not _has_valid_coordinates(record.lat, record.lon):
            continue

        items.append(
            LiveVesselMapItem(
                id=f"mmsi:{record.mmsi}",
                lat=record.lat,
                lon=record.lon,
                timestamp=record.time_utc,
                mmsi=record.mmsi,
                label=record.ship_name,
                course=record.cog,
                heading=record.true_heading,
                speed=record.sog,
            )
        )

    return items


def _default_ws_connect(url: str, open_timeout: float, **kwargs: Any) -> Any:
    try:
        import websockets
    except ImportError as exc:
        raise AisSourceError("websockets is required for AIS_SOURCE=aisstream") from exc

    return websockets.connect(url, open_timeout=open_timeout, **kwargs)


def _looks_like_source_error(message: dict[str, Any]) -> bool:
    return any(key.lower() in {"error", "errors"} for key in message)


def _has_valid_coordinates(lat: Any, lon: Any) -> bool:
    try:
        numeric_lat = float(lat)
        numeric_lon = float(lon)
    except (TypeError, ValueError):
        return False
    return -90 <= numeric_lat <= 90 and -180 <= numeric_lon <= 180


def _clean_ship_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)
