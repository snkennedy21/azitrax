from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import websockets

from app.config import AisSourceConfig


@dataclass
class ProbeMetrics:
    started: float
    duplicate_window_seconds: float
    received_frame_count: int = 0
    received_byte_count: int = 0
    ais_message_count: int = 0
    ais_byte_count: int = 0
    subscription_confirmation_count: int = 0
    invalid_message_count: int = 0
    invalid_json_count: int = 0
    invalid_envelope_count: int = 0
    invalid_position_report_count: int = 0
    provider_invalid_position_count: int = 0
    position_report_count: int = 0
    valid_position_report_count: int = 0
    exact_duplicate_count: int = 0
    previous_message_at: float | None = None
    max_inter_message_gap_seconds: float = 0.0
    max_gap_started_at_second: float | None = None
    max_gap_ended_at_second: float | None = None
    per_second: dict[int, dict[str, int]] = field(default_factory=dict)
    unique_mmsis: set[int] = field(default_factory=set)
    _seen_digests: dict[bytes, float] = field(default_factory=dict)
    _digest_queue: deque[tuple[float, bytes]] = field(default_factory=deque)

    def record_frame(self, raw_message: str | bytes, received_at: float) -> None:
        raw_bytes = _message_bytes(raw_message)
        message_bytes = len(raw_bytes)
        self.received_frame_count += 1
        self.received_byte_count += message_bytes

        try:
            message = json.loads(raw_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.invalid_json_count += 1
            self.invalid_message_count += 1
            return

        if not isinstance(message, dict) or not isinstance(message.get("MessageType"), str):
            self.invalid_envelope_count += 1
            self.invalid_message_count += 1
            return

        if message["MessageType"] == "SubscriptionConfirmation":
            self.subscription_confirmation_count += 1
            return

        self._record_ais_message(raw_bytes, message_bytes, message, received_at)

    def _record_ais_message(
        self,
        raw_bytes: bytes,
        message_bytes: int,
        message: dict[str, Any],
        received_at: float,
    ) -> None:
        self.ais_message_count += 1
        self.ais_byte_count += message_bytes
        self._record_gap(received_at)
        self._record_duplicate(raw_bytes, received_at)

        second = int(received_at - self.started)
        bucket = self.per_second.setdefault(
            second,
            {"message_count": 0, "byte_count": 0},
        )
        bucket["message_count"] += 1
        bucket["byte_count"] += message_bytes

        mmsi = _extract_mmsi(message)
        if mmsi is not None:
            self.unique_mmsis.add(mmsi)

        if message["MessageType"] != "PositionReport":
            return

        self.position_report_count += 1
        structurally_valid, provider_valid = _position_report_validity(message, mmsi)
        if not provider_valid:
            self.provider_invalid_position_count += 1

        if structurally_valid and provider_valid:
            self.valid_position_report_count += 1
            return

        self.invalid_position_report_count += 1
        self.invalid_message_count += 1

    def _record_gap(self, received_at: float) -> None:
        if self.previous_message_at is not None:
            gap_seconds = received_at - self.previous_message_at
            if gap_seconds > self.max_inter_message_gap_seconds:
                self.max_inter_message_gap_seconds = gap_seconds
                self.max_gap_started_at_second = self.previous_message_at - self.started
                self.max_gap_ended_at_second = received_at - self.started
        self.previous_message_at = received_at

    def _record_duplicate(self, raw_bytes: bytes, received_at: float) -> None:
        expires_before = received_at - self.duplicate_window_seconds
        while self._digest_queue and self._digest_queue[0][0] < expires_before:
            observed_at, expired_digest = self._digest_queue.popleft()
            if self._seen_digests.get(expired_digest) == observed_at:
                del self._seen_digests[expired_digest]

        digest = hashlib.blake2b(raw_bytes, digest_size=16).digest()
        if digest in self._seen_digests:
            self.exact_duplicate_count += 1

        self._seen_digests[digest] = received_at
        self._digest_queue.append((received_at, digest))

    def buckets(self, start_second: int, end_second: int) -> list[dict[str, int]]:
        return [
            {
                "second": second,
                "message_count": self.per_second.get(second, {}).get("message_count", 0),
                "byte_count": self.per_second.get(second, {}).get("byte_count", 0),
            }
            for second in range(start_second, end_second)
        ]

    def snapshot(self, elapsed_seconds: float) -> dict[str, int | float | None]:
        eligible_frame_count = (
            self.received_frame_count - self.subscription_confirmation_count
        )
        return {
            "received_frame_count": self.received_frame_count,
            "received_byte_count": self.received_byte_count,
            "ais_message_count": self.ais_message_count,
            "ais_byte_count": self.ais_byte_count,
            "ais_messages_per_second": self.ais_message_count / elapsed_seconds,
            "ais_bytes_per_second": self.ais_byte_count / elapsed_seconds,
            "subscription_confirmation_count": self.subscription_confirmation_count,
            "unique_mmsi_count": len(self.unique_mmsis),
            "exact_duplicate_count": self.exact_duplicate_count,
            "exact_duplicate_rate": _ratio(
                self.exact_duplicate_count,
                self.ais_message_count,
            ),
            "duplicate_window_seconds": self.duplicate_window_seconds,
            "invalid_message_count": self.invalid_message_count,
            "invalid_message_rate": _ratio(
                self.invalid_message_count,
                eligible_frame_count,
            ),
            "invalid_json_count": self.invalid_json_count,
            "invalid_envelope_count": self.invalid_envelope_count,
            "position_report_count": self.position_report_count,
            "valid_position_report_count": self.valid_position_report_count,
            "invalid_position_report_count": self.invalid_position_report_count,
            "provider_invalid_position_count": self.provider_invalid_position_count,
            "max_inter_message_gap_seconds": self.max_inter_message_gap_seconds,
            "max_gap_started_at_second": self.max_gap_started_at_second,
            "max_gap_ended_at_second": self.max_gap_ended_at_second,
        }


async def run_probe() -> None:
    config = AisSourceConfig.from_env()
    if not config.aisstream_api_key:
        raise RuntimeError("AISSTREAM_API_KEY is required")

    configured_duration_seconds = int(os.getenv("AIS_PROBE_DURATION_SECONDS", "60"))
    duration_seconds = (
        None
        if configured_duration_seconds == 0
        else max(1, configured_duration_seconds)
    )
    reconnect_backoff_seconds = max(
        0.0,
        float(os.getenv("AIS_PROBE_RECONNECT_BACKOFF_SECONDS", "5")),
    )
    checkpoint_seconds = max(
        1.0,
        float(os.getenv("AIS_PROBE_CHECKPOINT_SECONDS", "60")),
    )
    duplicate_window_seconds = max(
        0.0,
        float(os.getenv("AIS_PROBE_DUPLICATE_WINDOW_SECONDS", "300")),
    )

    subscription = {
        "APIKey": config.aisstream_api_key,
        "BoundingBoxes": config.aisstream_bounding_boxes,
        "FilterMessageTypes": config.aisstream_message_types,
    }

    started_at = datetime.now(timezone.utc)
    started = time.monotonic()
    deadline = (
        None
        if duration_seconds is None
        else started + duration_seconds
    )
    next_checkpoint_at = started + checkpoint_seconds
    last_checkpoint_second = 0
    metrics = ProbeMetrics(started, duplicate_window_seconds)
    output_path = os.getenv("AIS_PROBE_OUTPUT_PATH")
    output_file = None
    if output_path:
        output_file_path = Path(output_path)
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        output_file = output_file_path.open("a", encoding="utf-8")

    connection_attempt_count = 0
    successful_connection_count = 0
    connection_failure_count = 0
    disconnect_count = 0
    reconnect_attempt_count = 0
    reconnect_success_count = 0
    connection_events: list[dict[str, object]] = []
    observation_complete = False

    def build_record(
        record_type: str,
        elapsed_seconds: float,
        bucket_start: int,
        bucket_end: int,
    ) -> dict[str, object]:
        buckets = metrics.buckets(bucket_start, bucket_end)
        peak_messages = max(
            (bucket["message_count"] for bucket in metrics.per_second.values()),
            default=0,
        )
        peak_bytes = max(
            (bucket["byte_count"] for bucket in metrics.per_second.values()),
            default=0,
        )
        return {
            "record_type": record_type,
            "started_at": started_at.isoformat(),
            "duration_seconds": elapsed_seconds,
            **metrics.snapshot(elapsed_seconds),
            "peak_messages_per_second": peak_messages,
            "peak_bytes_per_second": peak_bytes,
            "connection_attempt_count": connection_attempt_count,
            "successful_connection_count": successful_connection_count,
            "connection_failure_count": connection_failure_count,
            "disconnect_count": disconnect_count,
            "reconnect_attempt_count": reconnect_attempt_count,
            "reconnect_success_count": reconnect_success_count,
            "connection_events": connection_events,
            "one_second_buckets": buckets,
        }

    def emit_due_checkpoint(now: float) -> None:
        nonlocal last_checkpoint_second, next_checkpoint_at
        if now < next_checkpoint_at:
            return

        elapsed_seconds = now - started
        completed_second = (
            int(elapsed_seconds)
            if duration_seconds is None
            else min(int(elapsed_seconds), duration_seconds)
        )
        checkpoint = build_record(
            "checkpoint",
            elapsed_seconds,
            last_checkpoint_second,
            completed_second,
        )
        _emit_record(checkpoint, output_file)
        last_checkpoint_second = completed_second
        while next_checkpoint_at <= now:
            next_checkpoint_at += checkpoint_seconds

    while not observation_complete:
        now = time.monotonic()
        emit_due_checkpoint(now)
        remaining_seconds = (
            float("inf") if deadline is None else deadline - now
        )
        if remaining_seconds <= 0:
            break

        connection_attempt_count += 1
        is_reconnect_attempt = successful_connection_count > 0
        if is_reconnect_attempt:
            reconnect_attempt_count += 1
        connected = False

        try:
            async with websockets.connect(
                config.aisstream_ws_url,
                open_timeout=min(
                    config.aisstream_connect_timeout_seconds,
                    remaining_seconds,
                ),
            ) as websocket:
                await websocket.send(json.dumps(subscription))
                connected = True
                if is_reconnect_attempt:
                    reconnect_success_count += 1
                successful_connection_count += 1
                connection_events.append(
                    {
                        "event": (
                            "connected"
                            if successful_connection_count == 1
                            else "reconnected"
                        ),
                        "at_second": time.monotonic() - started,
                    }
                )

                while True:
                    now = time.monotonic()
                    emit_due_checkpoint(now)
                    remaining_seconds = (
                        float("inf") if deadline is None else deadline - now
                    )
                    if remaining_seconds <= 0:
                        observation_complete = True
                        break

                    receive_timeout = min(
                        remaining_seconds,
                        max(0.001, next_checkpoint_at - now),
                    )
                    try:
                        async with asyncio.timeout(receive_timeout):
                            raw_message = await websocket.recv()
                    except TimeoutError:
                        if deadline is not None and time.monotonic() >= deadline:
                            observation_complete = True
                            break
                        continue

                    received_at = time.monotonic()
                    metrics.record_frame(raw_message, received_at)
        except Exception as exc:
            event = {
                "at_second": time.monotonic() - started,
                "error_type": type(exc).__name__,
            }
            if connected:
                disconnect_count += 1
                event["event"] = "disconnected"
            else:
                connection_failure_count += 1
                event["event"] = "connection_failed"
            connection_events.append(event)

        if observation_complete:
            break

        now = time.monotonic()
        emit_due_checkpoint(now)
        remaining_seconds = (
            float("inf") if deadline is None else deadline - now
        )
        if remaining_seconds <= 0:
            break
        await asyncio.sleep(min(reconnect_backoff_seconds, remaining_seconds))

    elapsed_seconds = time.monotonic() - started
    if duration_seconds is not None:
        bucket_count = max(duration_seconds, max(metrics.per_second, default=-1) + 1)
        final_record = build_record(
            "final",
            elapsed_seconds,
            0,
            bucket_count,
        )
        _emit_record(final_record, output_file)

    if output_file is not None:
        output_file.close()


def _emit_record(record: dict[str, object], output_file: Any) -> None:
    serialized = json.dumps(record, separators=(",", ":"))
    print(serialized, flush=True)
    if output_file is not None:
        output_file.write(serialized + "\n")
        output_file.flush()


def _message_bytes(raw_message: str | bytes) -> bytes:
    return raw_message.encode("utf-8") if isinstance(raw_message, str) else raw_message


def _extract_mmsi(message: dict[str, Any]) -> int | None:
    metadata = message.get("MetaData")
    metadata = metadata if isinstance(metadata, dict) else {}
    message_body = message.get("Message")
    message_body = message_body if isinstance(message_body, dict) else {}
    position_report = message_body.get("PositionReport")
    position_report = position_report if isinstance(position_report, dict) else {}
    value = metadata.get("MMSI", position_report.get("UserID"))
    try:
        mmsi = int(value)
    except (TypeError, ValueError):
        return None
    return mmsi if mmsi > 0 else None


def _position_report_validity(
    message: dict[str, Any],
    mmsi: int | None,
) -> tuple[bool, bool]:
    metadata = message.get("MetaData")
    metadata = metadata if isinstance(metadata, dict) else {}
    message_body = message.get("Message")
    message_body = message_body if isinstance(message_body, dict) else {}
    position_report = message_body.get("PositionReport")
    if not isinstance(position_report, dict):
        return False, True

    latitude = metadata.get(
        "latitude",
        metadata.get("Latitude", position_report.get("Latitude")),
    )
    longitude = metadata.get(
        "longitude",
        metadata.get("Longitude", position_report.get("Longitude")),
    )
    try:
        numeric_latitude = float(latitude)
        numeric_longitude = float(longitude)
    except (TypeError, ValueError):
        structurally_valid = False
    else:
        structurally_valid = (
            mmsi is not None
            and -90 <= numeric_latitude <= 90
            and -180 <= numeric_longitude <= 180
        )

    return structurally_valid, position_report.get("Valid") is not False


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def main() -> None:
    asyncio.run(run_probe())


if __name__ == "__main__":
    main()
