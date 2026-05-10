# Add Manual Smoke Test Checklist

## Description

Document a manual browser checklist for verifying the current Phase 0 geospatial workflow.

## Details

Some behavior is easiest to verify manually at this stage, especially OpenLayers rendering and click interactions. Add a concise checklist that a developer can follow after starting the local services.

The checklist should describe the current implemented behavior, not the earlier placeholder state.

Suggested scope:

- Document how to start the local services needed for the smoke test.
- Verify that the map loads.
- Verify that the API status indicator reports a connected state.
- Verify that create-point mode can be enabled.
- Verify that clicking the map creates a point marker.
- Verify that refreshing the browser still shows persisted points.
- Include a short troubleshooting note for backend/database connectivity.

## Acceptance Criteria

- A smoke test checklist exists in project documentation.
- The checklist reflects current implemented behavior.
- The checklist covers map load, API status, point creation, and refresh persistence.
- A developer can follow the checklist without reading source code.
- The checklist identifies the expected local URLs or commands needed to run the app.
