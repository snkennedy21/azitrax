from dataclasses import dataclass
import os
from typing import Annotated
from typing import Any

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from redis import Redis
from redis.exceptions import RedisError


@dataclass(frozen=True)
class RedisConfig:
    redis_url: str

    @classmethod
    def from_env(cls) -> "RedisConfig":
        return cls(redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))


def create_redis_client(config: RedisConfig | None = None) -> Redis:
    config = config or RedisConfig.from_env()
    return Redis.from_url(
        config.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def get_redis_client(request: Request) -> Redis:
    client = getattr(request.app.state, "redis_client", None)
    if client is None:
        raise RuntimeError("Redis client has not been initialized")

    return client


def check_redis_connection(client: Any) -> None:
    try:
        client.ping()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="redis unavailable") from exc


RedisClient = Annotated[Redis, Depends(get_redis_client)]
