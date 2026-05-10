# Real-Time Geospatial Tracking Platform Roadmap

## Project Direction

This project is a long-term engineering-focused geospatial application for ingesting, processing, transmitting, storing, and visualizing real-time spatial data.

The eventual platform should support multiple moving entity types, including:

- Aircraft
- Commercial ships
- Satellites
- Future moving entities such as drones, weather systems, emergency vehicles, or wildlife trackers

The project is intentionally not a CRUD application. The core learning goal is to build practical intuition around real-time data flow:

```text
Connect -> Ingest -> Normalize -> Transmit -> Render -> Store -> Scale
```

The current repository already contains a Phase 0 geospatial foundation:

- FastAPI backend
- PostgreSQL/PostGIS database
- Flyway migrations
- React frontend
- OpenLayers map
- Click-to-save point workflow
- Generated frontend API types from the backend OpenAPI schema

Because that foundation exists, the next work should not start by redesigning the app from scratch. It should build from the current Phase 0 loop toward live moving entities.

## Key Planning Decision

We decided not to start by designing full database schemas for tracked aircraft, ships, or satellites.

The reason is that the real external data shapes are not yet well understood. Designing persistence too early would risk encoding guesses into the database before seeing how source data actually behaves.

Instead, the next major product/engineering flow should be:

```text
confidence -> observe -> normalize lightly -> render -> learn -> model -> persist -> scale
```

In practical terms:

1. Establish a test and verification baseline.
2. Ingest real or realistic source data without persistence.
3. Normalize only enough to render and inspect it.
4. Poll from the frontend and display live entities on the map.
5. Learn from the actual data shape and UI needs.
6. Design persistence after observation.

This keeps the project aligned with the principle that architectural complexity should emerge naturally from real pressure.

## Epics

### 1. Establish Test and Verification Baseline

Goal: make the current Phase 0 app safe to extend.

This epic covers the existing click-to-save geospatial loop before new live-data work begins.

Primary work:

- Add backend test harness
- Add health endpoint tests
- Add point API tests
- Add coordinate validation and coordinate-order regression tests
- Establish frontend build/typecheck verification
- Add manual smoke-test checklist
- Clean up stale docs and debug artifacts

Outcome:

```text
Current app behavior is covered enough that we can build with confidence.
```

### 2. Live Source Discovery Without Persistence

Goal: touch real or realistic external data before designing database tables.

Primary work:

- Choose the first source, likely OpenSky aircraft data with a mock fallback
- Add a backend source-client module
- Fetch raw source payloads
- Add source configuration for URLs, limits, and timeouts
- Log or expose sample raw payloads for inspection
- Document observed fields, missing values, unusual cases, and useful metadata
- Add defensive handling for malformed records

Outcome:

```text
We understand the real aircraft data shape well enough to normalize it lightly.
```

### 3. Lightweight Live Entity Contract

Goal: define the smallest normalized shape needed to render moving things.

This is not the final persistence model. It is a temporary but useful live-data contract.

Possible shape:

```ts
LiveEntityPosition {
  source
  sourceId
  entityType
  lat
  lon
  timestamp
  label
  heading
  speed
  altitude
  metadata
}
```

Primary work:

- Add backend schemas for live entity positions
- Map raw aircraft records into the live entity contract
- Keep source-specific fields in metadata
- Validate required render fields
- Add normalization tests
- Generate updated frontend API types

Outcome:

```text
The backend can turn source-specific aircraft data into generic live map data.
```

### 4. Live Entity API

Goal: expose live entity positions to the frontend without storing them yet.

Primary work:

- Add `GET /live/entities`
- Return normalized live entity positions
- Support simple filters where useful
- Include freshness information
- Add API tests for response shape
- Define behavior when the source is unavailable
- Decide whether the endpoint fetches on request or reads from short-lived memory

Outcome:

```text
Frontend can ask the backend what moving entities are visible right now.
```

### 5. Polling-Based Live Map Rendering

Goal: render live aircraft on the existing OpenLayers map.

Primary work:

- Add React Query hook for live entities
- Poll the live endpoint every configured interval
- Add a separate OpenLayers vector layer for live entities
- Render aircraft markers
- Update marker positions without recreating the whole map
- Add selected-entity state
- Show selected entity details in the side panel
- Add loading, error, and stale-data states
- Keep point-create mode available as a development tool

Outcome:

```text
Aircraft appear on the map and update through polling.
```

### 6. Live Data UX and Inspection Tools

Goal: make the live map useful for understanding the data.

Primary work:

- Add selected entity detail panel
- Show source ID, callsign/label, altitude, speed, heading, timestamp, and metadata
- Add collapsible raw/debug metadata display
- Add filter controls for entity type/source
- Add freshness indicator
- Style fresh vs stale markers
- Add basic search by callsign/source ID
- Improve marker selection behavior

Outcome:

```text
The map becomes a data-inspection tool, not just dots on tiles.
```

### 7. Data Modeling Retrospective

Goal: design persistence after seeing real data move through the system.

Primary work:

- Review observed live payloads
- Identify generic fields shared by future aircraft, ships, and satellites
- Identify source-specific metadata
- Decide entity identity rules
- Decide what latest known position means
- Decide what position history should eventually store
- Draft `tracked_entities` schema
- Draft latest-position schema
- Draft position-history schema
- Document tradeoffs and open questions

Outcome:

```text
Database design is based on observed data instead of guesses.
```

### 8. Latest Position Persistence

Goal: store current known entity state in PostGIS.

Primary work:

- Add migrations for tracked entities
- Add migrations for latest positions
- Add spatial indexes
- Add repository/query functions
- Upsert latest positions from live source data
- Add database-backed entity endpoint
- Add tests for insert/update behavior
- Add tests for coordinate order and SRID
- Add tests for stale entity behavior

Outcome:

```text
Current aircraft positions survive backend/frontend refreshes and are queryable from PostGIS.
```

### 9. Spatial Querying and Viewport Filtering

Goal: make the backend geographically aware.

Primary work:

- Add bounding-box query support
- Add viewport parameters to the entity endpoint
- Use PostGIS spatial filtering
- Update frontend to request entities for the current viewport
- Debounce map-move requests
- Add result limits
- Add tests for bbox filtering
- Verify spatial index usage where practical

Outcome:

```text
The frontend can request only entities relevant to the current map view.
```

### 10. Historical Position Tracking

Goal: begin storing movement over time.

Primary work:

- Add `position_reports` table
- Append position reports during ingestion
- Define retention policy
- Add endpoint for entity trail/history
- Render selected entity trail on the map
- Add time-window query support
- Add tests for historical writes and queries
- Document storage-growth concerns

Outcome:

```text
The system can answer where an entity has been.
```

### 11. Replay and Time Controls

Goal: let users inspect movement over time.

Primary work:

- Add time-range controls
- Add replay state on the frontend
- Query historical positions by time window
- Render trails and replay marker
- Add playback speed controls
- Handle sparse or missing position reports
- Add UI states for no history available

Outcome:

```text
Users can replay recent movement instead of only seeing the present moment.
```

### 12. Realtime Streaming

Goal: move beyond polling when polling starts to feel limiting.

Primary work:

- Choose SSE or WebSockets
- Add streaming endpoint
- Push incremental entity updates
- Add client reconnection handling
- Add heartbeat/keepalive behavior
- Add client-side state reconciliation
- Compare streaming behavior against polling
- Keep polling fallback if useful

Outcome:

```text
The backend can push movement updates to connected clients.
```

### 13. Rendering Performance and Scale

Goal: handle larger volumes of spatial data smoothly.

Primary work:

- Measure current marker rendering performance
- Avoid unnecessary feature recreation
- Add clustering at lower zooms
- Add viewport culling
- Explore OpenLayers WebGL/vector rendering
- Add large fixture dataset
- Test marker update performance
- Add performance notes and thresholds

Outcome:

```text
The frontend remains smooth as entity counts grow.
```

### 14. Additional Entity Sources

Goal: validate that the platform works beyond aircraft.

Primary work:

- Add ship/AIS source discovery
- Add satellite/TLE source discovery
- Create source adapters using the same live entity contract
- Add entity-type-specific metadata handling
- Add map styling by aircraft, ship, and satellite
- Add filters by entity type
- Revisit the generic domain model after multiple sources

Outcome:

```text
The architecture proves it is a reusable moving-entity platform, not just an aircraft map.
```

### 15. Operational Visibility and Source Health

Goal: understand whether ingestion is healthy.

Primary work:

- Track last successful source fetch
- Track fetch duration and record counts
- Track malformed/skipped records
- Add source health endpoint
- Add backend logs around ingestion
- Show source status in the frontend
- Add failure-mode tests around unavailable or rate-limited sources

Outcome:

```text
When live data looks wrong, we can tell whether the source, backend, or frontend is the problem.
```

## Recommended Sequence

The recommended execution order is:

1. Establish Test and Verification Baseline
2. Live Source Discovery Without Persistence
3. Lightweight Live Entity Contract
4. Live Entity API
5. Polling-Based Live Map Rendering
6. Live Data UX and Inspection Tools
7. Data Modeling Retrospective
8. Latest Position Persistence
9. Spatial Querying and Viewport Filtering
10. Historical Position Tracking
11. Replay and Time Controls
12. Realtime Streaming
13. Rendering Performance and Scale
14. Additional Entity Sources
15. Operational Visibility and Source Health

## Guiding Principles

- Start from the existing Phase 0 app instead of rebuilding the foundation.
- Do not design database schemas before observing real source data.
- Normalize lightly before persistence.
- Prefer polling before streaming.
- Let architectural complexity emerge from actual bottlenecks.
- Keep source-specific details isolated from the generic moving-entity model.
- Use the map as a fast feedback loop for data quality, synchronization, and rendering behavior.
- Treat tests and verification as confidence tools, not ceremony.

