from fastapi import APIRouter
from fastapi import HTTPException
from psycopg import Error as PsycopgError

from app.cache.redis import check_redis_connection
from app.cache.redis import RedisClient
from app.db.connection import DbConnection


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    # This endpoint only proves the HTTP server is alive.
    # It does not touch Postgres.
    return {"status": "ok"}


@router.get("/health/db")
def database_health(db: DbConnection) -> dict[str, str]:
    # db is provided by FastAPI dependency injection. The DbConnection type
    # points to app.db.connection.get_db_connection, which borrows one connection
    # from the pool for this request and returns it afterward.
    try:
        # psycopg v3 lets a connection execute SQL directly. It returns a
        # cursor, and fetchone() reads the first row from that cursor.
        row = db.execute("SELECT 1 AS ok").fetchone()
    except PsycopgError as exc:
        # Translate database-driver errors into a useful HTTP response.
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    # A SELECT like this should always return one row. If it somehow does not,
    # treat that the same as an unavailable database.
    if row is None:
        raise HTTPException(status_code=503, detail="database unavailable")

    return {"status": "ok"}


@router.get("/health/redis")
def redis_health(redis_client: RedisClient) -> dict[str, str]:
    check_redis_connection(redis_client)
    return {"status": "ok"}
