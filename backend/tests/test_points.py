"""Tests for point creation and listing endpoints.

These tests verify the POST /points and GET /points endpoints work correctly,
including the write-then-read flow that confirms points are persisted to PostGIS.
"""

import pytest
from fastapi.testclient import TestClient
from psycopg import Connection


def assert_validation_error_for_field(response, field_name: str) -> None:
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"] == ["body", field_name] for error in errors)


def test_create_point_with_valid_coordinates(client: TestClient) -> None:
    """Test that POST /points creates a point with valid lat/lon coordinates.

    The endpoint should accept valid latitude and longitude values,
    store them in PostGIS, and return the created point with id and srid.
    """
    response = client.post(
        "/points",
        json={"lat": 37.7749, "lon": -122.4194}  # San Francisco coordinates
    )

    assert response.status_code == 201
    data = response.json()

    # Verify response includes all required fields
    assert "id" in data
    assert "lat" in data
    assert "lon" in data
    assert "srid" in data

    # Verify the coordinates match what was sent
    assert data["lat"] == 37.7749
    assert data["lon"] == -122.4194

    # Verify SRID is 4326 (WGS84)
    assert data["srid"] == 4326

    # Verify id is a positive integer
    assert isinstance(data["id"], int)
    assert data["id"] > 0


def test_get_points_returns_list(client: TestClient) -> None:
    """Test that GET /points returns a JSON array.

    The endpoint should return a list of points, even if empty.
    """
    response = client.get("/points")

    assert response.status_code == 200
    data = response.json()

    # Should return a list
    assert isinstance(data, list)


def test_get_points_returns_empty_list_when_no_points_exist(client: TestClient) -> None:
    """Test that GET /points returns empty array when database has no points.

    With the cleanup_database fixture, each test starts with an empty table.
    """
    response = client.get("/points")

    assert response.status_code == 200
    assert response.json() == []


def test_created_point_appears_in_get_points(client: TestClient) -> None:
    """Test write-then-read flow: point created via POST appears in GET response.

    This verifies that:
    1. POST /points successfully writes to the database
    2. GET /points successfully reads from the database
    3. The data round-trips correctly through PostGIS
    """
    # Create a point
    create_response = client.post(
        "/points",
        json={"lat": 40.7128, "lon": -74.0060}  # New York coordinates
    )

    assert create_response.status_code == 201
    created_point = create_response.json()

    # Retrieve all points
    get_response = client.get("/points")

    assert get_response.status_code == 200
    points = get_response.json()

    # Should have exactly one point
    assert len(points) == 1

    # The point should match what was created
    point = points[0]
    assert point["id"] == created_point["id"]
    assert point["lat"] == created_point["lat"]
    assert point["lon"] == created_point["lon"]


def test_multiple_points_can_be_created_and_retrieved(client: TestClient) -> None:
    """Test that multiple points can be created and all appear in GET response.

    This verifies the system can handle multiple points and maintains them
    in the expected order (by id).
    """
    # Create three points
    coordinates = [
        {"lat": 51.5074, "lon": -0.1278},    # London
        {"lat": 35.6762, "lon": 139.6503},   # Tokyo
        {"lat": -33.8688, "lon": 151.2093},  # Sydney
    ]

    created_ids = []
    for coords in coordinates:
        response = client.post("/points", json=coords)
        assert response.status_code == 201
        created_ids.append(response.json()["id"])

    # Retrieve all points
    response = client.get("/points")
    assert response.status_code == 200
    points = response.json()

    # Should have all three points
    assert len(points) == 3

    # Points should be ordered by id
    point_ids = [p["id"] for p in points]
    assert point_ids == sorted(point_ids)
    assert point_ids == created_ids

    # Verify coordinates match
    for i, point in enumerate(points):
        assert point["lat"] == coordinates[i]["lat"]
        assert point["lon"] == coordinates[i]["lon"]


@pytest.mark.parametrize("lat", [-90.000001, 90.000001])
def test_create_point_validates_latitude_bounds(
    client: TestClient,
    lat: float,
) -> None:
    """Test that POST /points rejects latitude values outside valid range.

    Latitude must be between -90 and 90 degrees.
    """
    response = client.post(
        "/points",
        json={"lat": lat, "lon": 0.0},
    )

    assert_validation_error_for_field(response, "lat")


@pytest.mark.parametrize("lon", [-180.000001, 180.000001])
def test_create_point_validates_longitude_bounds(
    client: TestClient,
    lon: float,
) -> None:
    """Test that POST /points rejects longitude values outside valid range.

    Longitude must be between -180 and 180 degrees.
    """
    response = client.post(
        "/points",
        json={"lat": 0.0, "lon": lon},
    )

    assert_validation_error_for_field(response, "lon")


def test_create_point_preserves_coordinate_order_and_srid(
    client: TestClient,
    db_connection: Connection,
) -> None:
    """Guard against reversing lat/lon at the PostGIS X/Y boundary."""
    submitted_lat = 12.345678
    submitted_lon = -98.765432

    create_response = client.post(
        "/points",
        json={"lat": submitted_lat, "lon": submitted_lon},
    )

    assert create_response.status_code == 201
    created_point = create_response.json()
    assert created_point["lat"] == pytest.approx(submitted_lat)
    assert created_point["lon"] == pytest.approx(submitted_lon)
    assert created_point["srid"] == 4326

    stored_point = db_connection.execute(
        """
        SELECT
            ST_Y(geom) AS lat,
            ST_X(geom) AS lon,
            ST_SRID(geom) AS srid
        FROM points
        WHERE id = %s
        """,
        (created_point["id"],),
    ).fetchone()

    assert stored_point is not None
    assert stored_point["lat"] == pytest.approx(submitted_lat)
    assert stored_point["lon"] == pytest.approx(submitted_lon)
    assert stored_point["srid"] == 4326

    get_response = client.get("/points")
    assert get_response.status_code == 200
    points = get_response.json()
    assert len(points) == 1
    assert points[0]["id"] == created_point["id"]
    assert points[0]["lat"] == pytest.approx(submitted_lat)
    assert points[0]["lon"] == pytest.approx(submitted_lon)


def test_create_point_accepts_boundary_values(client: TestClient) -> None:
    """Test that POST /points accepts valid boundary coordinate values.

    The endpoints should accept the extreme valid values for lat/lon.
    """
    # Test maximum latitude (North Pole)
    response = client.post(
        "/points",
        json={"lat": 90.0, "lon": 0.0}
    )
    assert response.status_code == 201

    # Test minimum latitude (South Pole)
    response = client.post(
        "/points",
        json={"lat": -90.0, "lon": 0.0}
    )
    assert response.status_code == 201

    # Test maximum longitude
    response = client.post(
        "/points",
        json={"lat": 0.0, "lon": 180.0}
    )
    assert response.status_code == 201

    # Test minimum longitude
    response = client.post(
        "/points",
        json={"lat": 0.0, "lon": -180.0}
    )
    assert response.status_code == 201
