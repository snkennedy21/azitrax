from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.live_vessels import router as live_vessels_router
from app.api.points import router as points_router
from app.cache import create_redis_client
from app.database import create_pool
from app.migrations import run_migrations
from app.migrations import validate_migrations


# FastAPI calls this function once when the app starts and resumes it once
# when the app shuts down. That makes it a good home for resources that should
# live for the whole process, like a database connection pool.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Run database migrations before opening connection pool.
    # This ensures schema is up-to-date before any API requests are processed.
    try:
        validate_migrations()
        run_migrations()
    except RuntimeError as exc:
        # Migration failures are fatal - log error and exit.
        # Docker will restart the container, retrying until migrations succeed.
        print(f"Fatal error during database migrations: {exc}")
        raise

    # Build the pool from environment variables in app.database.DatabaseConfig.
    # This does not run SQL yet; it prepares a reusable pool of connections.
    db_pool = create_pool()

    # Open the pool during startup so connection problems appear immediately
    # when the backend boots instead of surprising the first API request.
    db_pool.open()

    # app.state is FastAPI's place for storing process-wide objects. Later,
    # the database dependency reads this same pool from request.app.state.
    app.state.db_pool = db_pool
    app.state.redis_client = create_redis_client()

    try:
        # yield hands control back to FastAPI. The app serves requests until
        # shutdown, then execution continues in the finally block below.
        yield
    finally:
        app.state.redis_client.close()
        # Close all pooled database connections when the backend process exits.
        db_pool.close()


# Passing lifespan here tells FastAPI to run the startup/shutdown logic above.
app = FastAPI(title="Azitrax API", lifespan=lifespan)

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(live_vessels_router)
app.include_router(points_router)
