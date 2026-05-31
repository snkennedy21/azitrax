"""Tests for read-only point listing endpoints."""

from fastapi.testclient import TestClient


def test_post_points_is_disabled(client: TestClient) -> None:
    response = client.post(
        "/points",
        json={"lat": 37.7749, "lon": -122.4194},
    )

    assert response.status_code == 405


def test_get_points_returns_list(client: TestClient) -> None:
    """Test that GET /points returns a JSON array.

    The endpoint should return a list of points, even if empty.
    """
    response = client.get("/points")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)


def test_get_points_returns_empty_list_when_no_points_exist(client: TestClient) -> None:
    """Test that GET /points returns empty array when database has no points.

    With the cleanup_database fixture, each test starts with an empty table.
    """
    response = client.get("/points")

    assert response.status_code == 200
    assert response.json() == []
