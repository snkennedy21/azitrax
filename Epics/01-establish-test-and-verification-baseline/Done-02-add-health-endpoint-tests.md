# Add Health Endpoint Tests

## Description

Add automated tests for the backend health endpoints.

## Details

The backend exposes `/health` for application liveness and `/health/db` for database/PostGIS connectivity. These endpoints are important because they verify the local development stack before deeper geospatial behavior is tested.

Test `/health` as a simple application-level endpoint. Test `/health/db` in a way that clearly communicates whether a database-backed test environment is required.

Suggested scope:

- Test that `GET /health` returns a successful response.
- Test that the response includes `status: ok`.
- Test `GET /health/db` when the database is available.
- Assert that the database health response includes PostGIS version information.
- If database-backed tests require Docker Compose services, document that requirement.

## Acceptance Criteria

- `GET /health` is covered by an automated test.
- `GET /health/db` is covered by an automated test or explicitly marked as requiring the database test environment.
- Health tests verify response status codes and response bodies.
- A missing or unavailable database causes database health verification to fail clearly.
- Running the documented test command includes the health endpoint tests.
