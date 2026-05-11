# Add Backend Test Harness

## Description

Set up the backend test foundation so API and database behavior can be verified with a repeatable command.

## Details

The backend currently has working FastAPI routes and PostGIS integration, but no visible automated test suite. Add a minimal backend test setup that can exercise FastAPI endpoints and support future database-backed tests.

This ticket should establish the testing tools, directory structure, and documented command without trying to cover every route yet.

Suggested scope:

- Add `pytest` and any required FastAPI/httpx testing dependencies.
- Create a backend test directory.
- Add shared test setup for constructing or importing the FastAPI app.
- Decide how tests should be run locally, likely from the `backend` directory or through Docker Compose.
- Document the backend test command.

Avoid introducing a large testing framework or elaborate fixture system until the first real tests require it.

## Acceptance Criteria

- Backend tests can be run with one documented command.
- The test command exits successfully with at least one minimal passing test.
- Test dependencies are declared in the backend dependency configuration.
- The test structure is easy to extend for API and database-backed tests.
- Documentation explains how to run the backend test suite locally.
