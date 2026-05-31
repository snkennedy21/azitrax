from collections.abc import Iterator
from typing import Annotated
from typing import Any

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from psycopg import Connection
from psycopg import Error as PsycopgError
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool
from psycopg_pool import PoolTimeout

from app.config import DatabaseConfig


def create_pool(config: DatabaseConfig | None = None) -> ConnectionPool:
    # Tests or future code can pass a config directly. In normal app startup,
    # the config is read from environment variables.
    config = config or DatabaseConfig.from_env()

    # These kwargs are given to each real psycopg connection created by the
    # pool. dict_row makes query rows behave like dictionaries.
    connection_kwargs = {
        "connect_timeout": config.connect_timeout,
        "row_factory": dict_row,
    }

    # If DATABASE_URL is set, it already contains host/user/password/dbname.
    # If it is not set, pass the individual POSTGRES_* fields as kwargs.
    if not config.database_url:
        connection_kwargs.update(config.connection_kwargs())

    # open=False means "construct the pool object, but do not connect yet."
    # main.py explicitly calls db_pool.open() during FastAPI startup.
    return ConnectionPool(
        conninfo=config.database_url or "",
        kwargs=connection_kwargs,
        min_size=config.pool_min_size,
        max_size=config.pool_max_size,
        timeout=config.pool_timeout,
        open=False,
    )


def get_pool(app: Any) -> ConnectionPool:
    # main.py stores the pool on app.state during startup. This function is the
    # small central place that retrieves it for request-time database access.
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        # This should only happen if code asks for the pool before startup ran.
        raise RuntimeError("database pool has not been initialized")

    return pool


def get_db_connection(request: Request) -> Iterator[Connection[DictRow]]:
    # FastAPI calls this function automatically for route parameters typed as
    # DbConnection. The request gives us access to request.app.state.db_pool.
    pool = get_pool(request.app)
    try:
        # Borrow one connection from the pool for the duration of the request.
        # When the with block exits, psycopg_pool returns it to the pool.
        with pool.connection() as connection:
            # yield gives the borrowed connection to the route handler.
            yield connection
    except (PsycopgError, PoolTimeout) as exc:
        # PoolTimeout means no connection became available quickly enough.
        # PsycopgError covers lower-level database connection/query failures.
        raise HTTPException(status_code=503, detail="database unavailable") from exc


# This is a reusable FastAPI dependency type. A route can say `db: DbConnection`
# and receive a pooled psycopg connection without repeating Depends(...) there.
DbConnection = Annotated[Connection[DictRow], Depends(get_db_connection)]
