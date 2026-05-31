from fastapi import APIRouter
from fastapi import HTTPException
from redis.exceptions import RedisError

from app.cache.redis import RedisClient
from app.schemas.vessels import LiveVesselsResponse
from app.services.live_vessels import build_live_vessels_response


router = APIRouter(prefix="/live")


@router.get("/vessels")
def get_live_vessels(redis_client: RedisClient) -> LiveVesselsResponse:
    try:
        return build_live_vessels_response(redis_client)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="redis unavailable") from exc
