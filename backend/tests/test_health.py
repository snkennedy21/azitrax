"""Tests for health check endpoints.

These tests verify that the application and database health checks work correctly.
They serve as smoke tests to ensure the basic infrastructure is functioning.
"""

from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    """Test that /health endpoint returns 200 OK.

    This endpoint doesn't touch the database, so it should always succeed
    when the application is running.
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_endpoint_returns_ok(client: TestClient) -> None:
    """Test that /health/db endpoint returns 200 OK with PostGIS version.

    This endpoint queries the database to verify connectivity and that
    PostGIS extension is available.
    """
    response = client.get("/health/db")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "postgis_version" in data
    # PostGIS version should be a string like "3.4 USE_GEOS=1 USE_PROJ=1..."
    assert isinstance(data["postgis_version"], str)
    assert len(data["postgis_version"]) > 0


def test_database_health_uses_test_database(client: TestClient, db_connection) -> None:
    """Verify that tests are using the test database, not production.

    This is a safety test to ensure test isolation is working correctly.
    """
    # Query the database name directly
    row = db_connection.execute("SELECT current_database()").fetchone()
    db_name = row["current_database"]

    # Should be vector_test, not vector
    assert db_name == "vector_test", f"Tests are running against wrong database: {db_name}"
