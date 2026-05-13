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

import pytest
from fastapi.testclient import TestClient
from psycopg import Connection
from psycopg_pool import ConnectionPool

from app.database import create_pool, DatabaseConfig
from app.main import app


def pytest_sessionstart(session):
    """Run database migrations before test session starts.

    This runs once before any tests execute, ensuring the test database
    schema is up-to-date. Migrations are applied to TEST_POSTGRES_DB.
    """
    # Use POSTGRES_HOST from main app config if available (set to 'db' in Docker),
    # otherwise default to 127.0.0.1 for local testing
    default_host = os.getenv("POSTGRES_HOST", "127.0.0.1")

    # Set environment variables for Flyway to use test database
    # Only override database name and optionally host - reuse credentials and port
    test_env = os.environ.copy()
    test_env.update({
        "POSTGRES_HOST": os.getenv("TEST_POSTGRES_HOST", default_host),
        "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "5432"),
        "POSTGRES_DB": os.getenv("TEST_POSTGRES_DB", "vector_test"),
        "POSTGRES_USER": os.getenv("POSTGRES_USER", "vector"),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "vector"),
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

    Reuses production database credentials and settings, but connects to
    a separate test database (TEST_POSTGRES_DB). Optionally override host
    with TEST_POSTGRES_HOST for local testing.

    Defaults to 'db' hostname for Docker, or '127.0.0.1' for local.
    """
    # Use POSTGRES_HOST from main app config if available (set to 'db' in Docker),
    # otherwise default to 127.0.0.1 for local testing
    default_host = os.getenv("POSTGRES_HOST", "127.0.0.1")

    return DatabaseConfig(
        database_url=None,  # Build from components instead
        host=os.getenv("TEST_POSTGRES_HOST", default_host),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("TEST_POSTGRES_DB", "vector_test"),
        user=os.getenv("POSTGRES_USER", "vector"),
        password=os.getenv("POSTGRES_PASSWORD", "vector"),
        connect_timeout=int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "5")),
        pool_min_size=int(os.getenv("POSTGRES_POOL_MIN_SIZE", "1")),
        pool_max_size=int(os.getenv("POSTGRES_POOL_MAX_SIZE", "5")),
        pool_timeout=float(os.getenv("POSTGRES_POOL_TIMEOUT", "5")),
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
