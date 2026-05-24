from __future__ import annotations

"""Shared pytest fixtures for FastAPI testing.

This module provides fixtures for:
- Test database configuration
- FastAPI application with test database
- HTTP test client
- Database connection pool
- Database cleanup between tests
"""

import os
import subprocess
import sys
from collections.abc import Iterator
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest
from fastapi.testclient import TestClient
from psycopg import Connection
from psycopg_pool import ConnectionPool

from app.database import create_pool, DatabaseConfig
from app.main import app


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.sets: dict[str, set[object]] = {}
        self.expires_at: dict[str, datetime] = {}

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        return None

    def get(self, key: str) -> str | None:
        if self._is_expired(key):
            self.values.pop(key, None)
            self.expires_at.pop(key, None)
            return None

        return self.values.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value
        if ex is None:
            self.expires_at.pop(key, None)
        else:
            self.expires_at[key] = datetime.now(timezone.utc) + timedelta(seconds=ex)

    def mget(self, keys: list[str]) -> list[str | None]:
        return [self.get(key) for key in keys]

    def smembers(self, key: str) -> set[object]:
        return self.sets.get(key, set())

    def sadd(self, key: str, *values: object) -> None:
        self.sets.setdefault(key, set()).update(values)

    def srem(self, key: str, *values: object) -> None:
        self.sets.setdefault(key, set()).difference_update(values)

    def expire_now(self, key: str) -> None:
        self.expires_at[key] = datetime.now(timezone.utc) - timedelta(seconds=1)

    def _is_expired(self, key: str) -> bool:
        expires_at = self.expires_at.get(key)
        return expires_at is not None and expires_at <= datetime.now(timezone.utc)


def pytest_sessionstart(session):
    """Run database migrations before test session starts.

    This runs once before any tests execute, ensuring the test database
    schema is up-to-date. Migrations are applied to TEST_POSTGRES_DB.
    """
    # Flyway reads POSTGRES_* from flyway.conf. Build those values from the
    # dedicated TEST_POSTGRES_* environment so test migrations cannot inherit
    # the app's normal database target.
    test_env = os.environ.copy()
    test_env.pop("DATABASE_URL", None)
    test_env.update({
        "POSTGRES_HOST": os.getenv("TEST_POSTGRES_HOST", "db"),
        "POSTGRES_PORT": os.getenv("TEST_POSTGRES_PORT", "5432"),
        "POSTGRES_DB": os.getenv("TEST_POSTGRES_DB", "vector_test"),
        "POSTGRES_USER": os.getenv("TEST_POSTGRES_USER", "vector"),
        "POSTGRES_PASSWORD": os.getenv("TEST_POSTGRES_PASSWORD", "vector"),
    })

    print("\n" + "=" * 80, file=sys.stderr)
    print("Running test database migrations...", file=sys.stderr)
    print(f"Database: {test_env['POSTGRES_DB']} at {test_env['POSTGRES_HOST']}", file=sys.stderr)
    print("=" * 80, file=sys.stderr)

    # Get the backend directory path
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    flyway_config = os.path.join(backend_dir, "flyway.conf")

    # Run Flyway migrations using the same flyway.conf as production
    result = subprocess.run(
        [
            "flyway",
            f"-configFiles={flyway_config}",
            "migrate"
        ],
        env=test_env,
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("MIGRATION FAILED!", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        pytest.exit("Test database migrations failed", returncode=1)

    print("Test database migrations completed successfully!", file=sys.stderr)
    print("=" * 80 + "\n", file=sys.stderr)


@pytest.fixture(scope="session")
def test_db_config() -> DatabaseConfig:
    """Database configuration for tests.

    Uses dedicated TEST_POSTGRES_* settings so tests stay isolated from the
    app's normal database configuration.
    """
    return DatabaseConfig(
        database_url=None,  # Build from components instead
        host=os.getenv("TEST_POSTGRES_HOST", "db"),
        port=int(os.getenv("TEST_POSTGRES_PORT", "5432")),
        dbname=os.getenv("TEST_POSTGRES_DB", "vector_test"),
        user=os.getenv("TEST_POSTGRES_USER", "vector"),
        password=os.getenv("TEST_POSTGRES_PASSWORD", "vector"),
        connect_timeout=int(os.getenv("TEST_POSTGRES_CONNECT_TIMEOUT", "5")),
        pool_min_size=int(os.getenv("TEST_POSTGRES_POOL_MIN_SIZE", "1")),
        pool_max_size=int(os.getenv("TEST_POSTGRES_POOL_MAX_SIZE", "5")),
        pool_timeout=float(os.getenv("TEST_POSTGRES_POOL_TIMEOUT", "5")),
    )


@pytest.fixture(scope="session")
def test_db_pool(test_db_config: DatabaseConfig) -> Iterator[ConnectionPool]:
    """Create and manage a database connection pool for tests.

    The pool is created once per test session and shared across all tests.
    This is more efficient than creating a pool per test.
    """
    pool = create_pool(test_db_config)
    pool.open()
    yield pool
    pool.close()


@pytest.fixture
def db_connection(test_db_pool: ConnectionPool) -> Iterator[Connection]:
    """Provide a database connection for a single test.

    The connection is borrowed from the pool and returned after the test.
    This fixture is function-scoped so each test gets a fresh connection.
    """
    with test_db_pool.connection() as conn:
        yield conn


@pytest.fixture
def client(test_db_pool: ConnectionPool) -> Iterator[TestClient]:
    """Provide a FastAPI TestClient with test database.

    This fixture overrides the app's database pool to use the test database.
    The test pool is opened by the test_db_pool fixture, so this client avoids
    running the app lifespan that would create a production database pool.
    """
    # Override the db_pool in app.state to use test database
    app.state.db_pool = test_db_pool
    app.state.redis_client = FakeRedisClient()

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()


@pytest.fixture(autouse=True)
def cleanup_database(db_connection: Connection) -> Iterator[None]:
    """Clean up database between tests.

    This fixture runs automatically for every test (autouse=True).
    It truncates all tables after each test to ensure isolation.
    """
    db_connection.execute("TRUNCATE TABLE points RESTART IDENTITY CASCADE")
    db_connection.commit()

    try:
        yield  # Test runs here
    finally:
        db_connection.execute("TRUNCATE TABLE points RESTART IDENTITY CASCADE")
        db_connection.commit()
