# Add Point API Tests

## Description

Add automated tests for the existing point creation and point listing API.

## Details

The current Phase 0 loop depends on `POST /points` and `GET /points`. These routes should be covered before the project adds live moving entities, because they verify the existing API-to-PostGIS path.

The tests should confirm that a point can be written, read back, and returned with the expected response shape.

Suggested scope:

- Test `POST /points` with valid latitude and longitude.
- Test that the creation response includes `id`, `lat`, `lon`, and `srid`.
- Test that `GET /points` returns a JSON array.
- Test that a point created through `POST /points` appears in a later `GET /points` response.
- Ensure tests are isolated enough that repeated test runs do not fail because of existing data.

## Acceptance Criteria

- Valid point creation is covered by an automated test.
- Point listing is covered by an automated test.
- A write-then-read flow is covered by an automated test.
- Tests assert the expected API response shape.
- Tests can be run repeatedly without depending on a manually cleaned database.
