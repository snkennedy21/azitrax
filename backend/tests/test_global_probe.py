from __future__ import annotations

import json

import pytest

from app.ais.global_probe import ProbeMetrics


def position_report(
    *,
    mmsi: int = 123456789,
    latitude: float = 40.5,
    longitude: float = -73.9,
    valid: bool = True,
) -> bytes:
    return json.dumps(
        {
            "MessageType": "PositionReport",
            "MetaData": {
                "MMSI": mmsi,
                "latitude": latitude,
                "longitude": longitude,
            },
            "Message": {
                "PositionReport": {
                    "UserID": mmsi,
                    "Latitude": latitude,
                    "Longitude": longitude,
                    "Valid": valid,
                }
            },
        },
        separators=(",", ":"),
    ).encode()


def test_records_ais_metrics_and_excludes_subscription_confirmation() -> None:
    metrics = ProbeMetrics(started=100.0, duplicate_window_seconds=300.0)
    confirmation = json.dumps(
        {
            "MessageType": "SubscriptionConfirmation",
            "Message": {"CompressionEnabled": True},
        }
    ).encode()

    metrics.record_frame(confirmation, 100.1)
    metrics.record_frame(position_report(), 100.2)

    snapshot = metrics.snapshot(elapsed_seconds=1.0)
    assert snapshot["received_frame_count"] == 2
    assert snapshot["subscription_confirmation_count"] == 1
    assert snapshot["ais_message_count"] == 1
    assert snapshot["unique_mmsi_count"] == 1
    assert snapshot["valid_position_report_count"] == 1
    assert metrics.buckets(0, 1)[0]["message_count"] == 1


def test_counts_exact_duplicates_only_within_configured_window() -> None:
    metrics = ProbeMetrics(started=100.0, duplicate_window_seconds=5.0)
    message = position_report()

    metrics.record_frame(message, 101.0)
    metrics.record_frame(message, 104.0)
    metrics.record_frame(message, 110.0)

    snapshot = metrics.snapshot(elapsed_seconds=10.0)
    assert snapshot["ais_message_count"] == 3
    assert snapshot["exact_duplicate_count"] == 1
    assert snapshot["exact_duplicate_rate"] == pytest.approx(1 / 3)


def test_counts_invalid_json_envelopes_and_positions() -> None:
    metrics = ProbeMetrics(started=100.0, duplicate_window_seconds=300.0)

    metrics.record_frame(b"not json", 100.1)
    metrics.record_frame(b"{}", 100.2)
    metrics.record_frame(position_report(valid=False), 100.3)
    metrics.record_frame(position_report(latitude=91), 100.4)

    snapshot = metrics.snapshot(elapsed_seconds=1.0)
    assert snapshot["invalid_json_count"] == 1
    assert snapshot["invalid_envelope_count"] == 1
    assert snapshot["provider_invalid_position_count"] == 1
    assert snapshot["invalid_position_report_count"] == 2
    assert snapshot["invalid_message_count"] == 4
    assert snapshot["invalid_message_rate"] == 1.0


def test_records_longest_gap_between_ais_messages() -> None:
    metrics = ProbeMetrics(started=100.0, duplicate_window_seconds=300.0)

    metrics.record_frame(position_report(mmsi=111111111), 101.0)
    metrics.record_frame(position_report(mmsi=222222222), 101.25)
    metrics.record_frame(position_report(mmsi=333333333), 103.0)

    snapshot = metrics.snapshot(elapsed_seconds=3.0)
    assert snapshot["max_inter_message_gap_seconds"] == pytest.approx(1.75)
    assert snapshot["max_gap_started_at_second"] == pytest.approx(1.25)
    assert snapshot["max_gap_ended_at_second"] == pytest.approx(3.0)
