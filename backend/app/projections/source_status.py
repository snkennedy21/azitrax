from datetime import datetime
from datetime import timezone
import json
from typing import Any

from app.cache.redis import LIVE_AIS_STATUS_KEY
from app.config import AisSourceConfig


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
        "consumerStartedAt": (
            observed_at.isoformat()
            if status == "connecting"
            else previous_status.get("consumerStartedAt")
        ),
        "lastSuccessfulMessageAt": _preserved_timestamp(
            previous_status, "lastSuccessfulMessageAt", last_successful_message_at
        ),
        "lastRenderableMessageAt": _preserved_timestamp(
            previous_status, "lastRenderableMessageAt", last_renderable_message_at
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


def consumer_health_check(redis_client: Any, max_age_seconds: float) -> None:
    redis_client.ping()
    status = read_source_status(redis_client)
    if status.get("status") != "connected":
        raise RuntimeError(f"consumer status is {status.get('status', 'missing')}")

    last_renderable = status.get("lastRenderableMessageAt")
    if not isinstance(last_renderable, str):
        raise RuntimeError("consumer has not persisted a renderable message")

    try:
        processed_at = datetime.fromisoformat(last_renderable)
        started_at_value = status.get("consumerStartedAt")
        started_at = (
            datetime.fromisoformat(started_at_value)
            if isinstance(started_at_value, str)
            else None
        )
    except ValueError as exc:
        raise RuntimeError("consumer progress timestamp is invalid") from exc

    processed_at = processed_at.astimezone(timezone.utc)
    if started_at is not None and processed_at < started_at.astimezone(timezone.utc):
        raise RuntimeError("consumer has not progressed since it started")

    age = (datetime.now(timezone.utc) - processed_at).total_seconds()
    if age > max_age_seconds:
        raise RuntimeError(f"consumer progress is {age:.0f}s old")


def _preserved_timestamp(
    previous_status: dict[str, Any],
    key: str,
    value: datetime | None,
) -> str | None:
    if value is not None:
        return value.isoformat()

    previous_value = previous_status.get(key)
    return previous_value if isinstance(previous_value, str) else None
