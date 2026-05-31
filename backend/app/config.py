from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_AIS_BOUNDING_BOXES = [[[40.4774, -74.2591], [40.9176, -73.7004]]]
DEFAULT_AIS_FIXTURE_PATH = Path(__file__).resolve().parent / "ais/fixtures/aisstream-position-reports-sample.json"


@dataclass(frozen=True)
class DatabaseConfig:
    database_url: str | None
    host: str
    port: int
    dbname: str
    user: str
    password: str
    connect_timeout: int
    pool_min_size: int
    pool_max_size: int
    pool_timeout: float

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        return cls(
            database_url=os.getenv("DATABASE_URL"),
            host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "azitrax"),
            user=os.getenv("POSTGRES_USER", "azitrax"),
            password=os.getenv("POSTGRES_PASSWORD", "azitrax"),
            connect_timeout=int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "5")),
            pool_min_size=int(os.getenv("POSTGRES_POOL_MIN_SIZE", "1")),
            pool_max_size=int(os.getenv("POSTGRES_POOL_MAX_SIZE", "5")),
            pool_timeout=float(os.getenv("POSTGRES_POOL_TIMEOUT", "5")),
        )

    def connection_kwargs(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
            "connect_timeout": self.connect_timeout,
        }


@dataclass(frozen=True)
class RedisConfig:
    redis_url: str

    @classmethod
    def from_env(cls) -> RedisConfig:
        return cls(redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))


@dataclass(frozen=True)
class AisSourceConfig:
    source: str = "fixture"
    fixture_path: Path = DEFAULT_AIS_FIXTURE_PATH
    allow_fixture_fallback: bool = True
    aisstream_ws_url: str = "wss://stream.aisstream.io/v0/stream"
    aisstream_api_key: str | None = None
    aisstream_bounding_boxes: list[Any] | None = None
    aisstream_message_types: list[str] | None = None
    aisstream_connect_timeout_seconds: float = 30.0
    aisstream_sample_message_limit: int = 50
    aisstream_disable_tls_verify: bool = False

    @classmethod
    def from_env(cls) -> AisSourceConfig:
        return cls(
            source=os.getenv("AIS_SOURCE", "fixture").strip().lower(),
            fixture_path=_resolve_path(os.getenv("AIS_FIXTURE_PATH"), DEFAULT_AIS_FIXTURE_PATH),
            allow_fixture_fallback=_parse_bool(os.getenv("AIS_ALLOW_FIXTURE_FALLBACK", "true")),
            aisstream_ws_url=os.getenv("AISSTREAM_WS_URL", "wss://stream.aisstream.io/v0/stream"),
            aisstream_api_key=os.getenv("AISSTREAM_API_KEY") or None,
            aisstream_bounding_boxes=_parse_json_env("AISSTREAM_BOUNDING_BOXES", DEFAULT_AIS_BOUNDING_BOXES),
            aisstream_message_types=_parse_csv_env("AISSTREAM_MESSAGE_TYPES", ["PositionReport"]),
            aisstream_connect_timeout_seconds=float(os.getenv("AISSTREAM_CONNECT_TIMEOUT_SECONDS", "30")),
            aisstream_sample_message_limit=max(1, int(os.getenv("AISSTREAM_SAMPLE_MESSAGE_LIMIT", "50"))),
            aisstream_disable_tls_verify=_parse_bool(os.getenv("AISSTREAM_DISABLE_TLS_VERIFY", "false")),
        )


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


def frontend_origins_from_env() -> list[str]:
    return [
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv_env(name: str, default: list[str]) -> list[str]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return [part.strip() for part in raw_value.split(",") if part.strip()]


def _parse_json_env(name: str, default: list[Any]) -> list[Any]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} must be valid JSON") from exc
    if not isinstance(parsed, list):
        raise ValueError(f"{name} must be a JSON array")
    return parsed


def _resolve_path(raw_path: str | None, default: Path) -> Path:
    if not raw_path:
        return default

    path = Path(raw_path)
    if path.is_absolute():
        if path.exists():
            return path
        if path.name == default.name and default.exists():
            return default
        return path
    return Path(__file__).resolve().parents[1] / path
