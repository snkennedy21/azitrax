# Global AIS Platform Roadmap

## Purpose

Evolve Azitrax from a bounding-box live-vessel demonstration into a globally
ingested AIS platform that can serve hundreds of concurrent map users and retain
historical vessel movement.

This is a living roadmap. It records decisions already made, identifies the
module seams that should remain stable, and sequences implementation so that
each phase produces a measurable, operable improvement.

## Confirmed Product Decisions

- Ingest all globally available AIS data rather than limiting product coverage
  to selected regions.
- Treat provider coverage as the practical limit of "global." Missing receiver
  coverage or provider outages must not be represented as proof that no vessels
  exist in an area.
- Show stable geographic clusters with vessel counts at world and regional zoom
  levels.
- Show individual directional vessel markers only when zoom and density permit.
- Design serving infrastructure for hundreds of concurrent users.
- Permit live map presentation to lag source ingestion by minutes when that
  materially improves performance and cacheability.
- Build individual vessel trails before attempting full-world historical replay.
- Retain full-fidelity raw positions for a defined period, then preserve useful
  historical movement through an archival or downsampling policy.
- A selected vessel does not need to remain selected after it leaves the active
  map result.
- Do not intentionally lose a position after it has been durably accepted by
  Azitrax.

## Reliability Guarantee

"No data loss" means that every source message durably accepted by Azitrax can
be replayed until its downstream processing succeeds. It does not mean Azitrax
can recover messages that the provider never delivered during an upstream or
network outage.

The ingestion path must therefore record the original source envelope durably
before normal validation, normalization, live projection, or historical storage.
Invalid or temporarily unsupported envelopes must remain available for audit
and reprocessing.

The system must:

- Detect and report source connection gaps.
- Retry downstream processing without corrupting state.
- Make consumers idempotent so replays do not create incorrect duplicates.
- Track processing checkpoints and backlog age.
- Quarantine poison messages without blocking the rest of the stream.

Whether true end-to-end recovery is possible depends on whether the source
provider offers replay, sequence identifiers, or historical gap recovery.

This is the target guarantee, not the initial delivery state. Until Phase 6 is
complete, ingestion and history are explicitly best-effort. Earlier phases must
still use stable event identities and idempotent processing so durability can be
added at the established seam without rewriting live maps, clusters, or trails.

## Current State

The current implementation is intentionally optimized for a small discovery
area:

```text
AISStream bounding boxes
        -> continuous consumer
        -> latest vessel per MMSI in Redis
        -> one global MMSI set
        -> GET /live/vessels returns the complete live snapshot
        -> each browser polls every 10 seconds
        -> OpenLayers rebuilds all vessel features
```

This design proves the source and rendering path, but it couples acquisition
scope, retained state, response size, and browser rendering cost. A global
snapshot cannot be sent to every browser.

## Target System Shape

```text
Global AIS source adapter
          |
          v
Durable ingestion journal
          |
          v
Position processing module
     |                 |
     v                 v
Historical position    Live-position projection
module                  module
     |                 |
     +--------+--------+
              v
       Map snapshot module
       |                 |
       v                 v
Stable clusters     Individual vessels
              |
              v
      Cacheable HTTP/tile adapter
              |
              v
           OpenLayers
```

The ingestion rate and browser refresh rate are intentionally independent.
Ingestion remains continuous for historical fidelity, while map snapshots may
be cached for tens of seconds or minutes.

## Module Responsibilities and Interfaces

### Source adapter

Owns the provider connection, subscription, reconnect behavior, and source
envelope capture. It does not own normalization or storage policy.

Conceptual interface:

```text
receive() -> SourceEnvelope
```

### Durable ingestion module

Accepts a source envelope and returns only after the envelope satisfies the
configured durability guarantee. It owns replay, checkpoints, retries, and
poison-message handling behind a small interface.

Conceptual interface:

```text
append(SourceEnvelope) -> DurableReceipt
readAfter(Checkpoint) -> SourceEnvelope stream
```

### Position processing module

Converts durable source envelopes into normalized position events. It owns
validation, source-time parsing, deduplication, out-of-order handling, and data
quality classification.

Conceptual result:

```text
PositionEvent {
  eventId
  source
  mmsi
  sourceTimestamp
  observedTimestamp
  coordinates
  course
  heading
  speed
  quality
}
```

### Historical position module

Stores append-only normalized positions and serves time-range tracks for one
vessel. Storage should be time-partitioned and spatially indexed. Retention and
downsampling are implementation policies, not caller concerns.

Conceptual interface:

```text
record(PositionEvent)
getTrack(mmsi, timeRange, resolution) -> VesselTrack
```

### Live-position projection module

Maintains the latest accepted position per MMSI and supports efficient spatial
queries. Redis may remain part of this implementation, but the current global
set scan cannot be its long-term query interface.

Conceptual interface:

```text
project(PositionEvent)
query(viewport, freshnessCutoff) -> latest vessel positions
```

### Map snapshot module

Hides storage, clustering, result budgets, and level-of-detail decisions from
the browser. A caller supplies a viewport, zoom, and optional historical time;
the module returns either clusters or vessels.

Conceptual interface:

```text
queryMapSnapshot(viewport, zoom, at?) -> MapSnapshot
```

```text
MapSnapshot =
  ClusterSnapshot {
    clusters
    asOf
  }
  | VesselSnapshot {
    vessels
    asOf
    matchedCount
    returnedCount
    truncated
  }
```

### Frontend map module

Requests only the tiles or buffered viewport needed for the current map view.
It renders clusters at low detail and individual vessels at high detail. It
does not implement clustering or silently sample oversized results.

## Delivery Principles

- Build vertical slices that can run in production before replacing the current
  path.
- Shadow-write and compare new projections before switching reads.
- Keep global ingestion independent of the number of connected browser users.
- Prefer stable tile or cell aggregation over clusters that visibly jump on
  every refresh.
- Normalize requests to tiles where practical so users share cached responses.
- Enforce result budgets on the server and expose truncation in metadata.
- Aggregate dense results rather than randomly dropping vessels.
- Preserve raw source envelopes long enough to reprocess schema and parsing
  mistakes.
- Defer the durable journal implementation until the serving path is proven,
  but establish stable event identities and idempotent processing first.
- Label all history collected before durable ingestion as best-effort and do
  not imply that it is complete.
- Measure before fixing permanent marker, refresh, and retention limits.

## Phased Roadmap

### Phase 0: Validate the global source and establish capacity baselines

#### Objectives

- Confirm that the provider permits a global subscription at the required rate.
- Measure real global message volume, bursts, duplication, reconnect behavior,
  and source coverage gaps.
- Establish storage, processing, serving, and browser performance baselines.

#### Deliverables

- A controlled global-ingestion probe that does not feed production state.
- Metrics for messages per second, peak bursts, bytes per message, unique MMSIs,
  duplicate rate, invalid rate, and disconnect frequency.
- An estimate of raw storage growth per day.
- Documented provider limits, data rights, and replay capabilities.
- A repeatable synthetic load fixture based on observed distributions with
  identifying source content removed where necessary.

#### Exit criteria

- Global subscription behavior is understood well enough to size the durable
  path.
- Capacity estimates include normal load and a defined burst multiplier.
- Provider limitations and unavoidable loss scenarios are documented.

### Phase 1: Establish replay-safe event processing

#### Objectives

- Define stable source and position event contracts before expanding the
  serving path.
- Make processing idempotent so a durable journal can be inserted later without
  rewriting downstream modules.

#### Deliverables

- `SourceEnvelope` and `PositionEvent` representations with stable identities.
- Explicit deduplication and out-of-order rules.
- Idempotent position processing and projection writes.
- Source-gap, invalid-message, duplicate, and processing-failure metrics.
- Replay tests that process the same recorded fixture repeatedly and produce the
  same outcome.
- A documented seam where durable ingestion will later be inserted.

#### Exit criteria

- Reprocessing an event cannot create incorrect history or live state.
- Event identity remains stable across source reconnects and fixture replay.
- Downstream modules do not depend directly on the AISStream transport shape.
- The system clearly reports that ingestion remains best-effort at this phase.

### Phase 2: Build the global live-position projection

#### Objectives

- Replace global set scans with spatial latest-position queries.
- Keep the projection rebuildable from replay-safe position events.

#### Deliverables

- Latest accepted position per MMSI.
- Spatial query by viewport or tile.
- Freshness and expiration semantics preserved or deliberately revised.
- Projection rebuild and reconciliation procedure using recorded fixtures.
- Shadow comparison against the current Redis snapshot for a defined period.
- Metrics for projection lag, vessel count, stale count, query latency, and
  reconciliation differences.

#### Exit criteria

- Spatial queries do not scan every known MMSI.
- Replaying the same position events rebuilds the same projection.
- Shadow results meet the agreed correctness threshold.
- Projection performance is measured under representative global load.

### Phase 3: Add level-of-detail map snapshots and clusters

#### Objectives

- Serve global maps without returning global vessel lists.
- Produce stable, cacheable clusters at low and regional zoom levels.

#### Deliverables

- Tile- or cell-aligned cluster identifiers and bounds.
- Cluster responses with vessel counts and snapshot time.
- Individual-vessel responses for sufficiently detailed views.
- Server-enforced result budget and response metadata.
- Cache policy suitable for live data that may lag by minutes.
- Load tests covering hundreds of concurrent users with overlapping and
  non-overlapping map views.

#### Exit criteria

- A world view has bounded response size independent of total vessel count.
- Dense viewports aggregate rather than truncate vessels silently.
- Shared views achieve a useful cache-hit rate.
- Serving load remains within agreed limits for hundreds of concurrent users.

### Phase 4: Move the frontend to viewport-aware rendering

#### Objectives

- Query by visible map area and zoom instead of polling the full live snapshot.
- Render clusters and individual vessels through one map interaction model.

#### Deliverables

- Buffered viewport or tile queries triggered after map movement settles.
- Cancellation of obsolete requests during navigation.
- Cluster markers displaying vessel counts.
- Cluster click behavior that zooms to cluster bounds.
- Individual vessel markers and existing popup behavior at detailed zoom.
- Loading and snapshot-age indicators.
- Instrumentation for response bytes, feature update time, frame time, and
  browser memory.

#### Exit criteria

- Panning and zooming never requests the full global vessel population.
- World and regional views remain readable and responsive.
- Individual vessel rendering stays within a measured browser budget.
- Empty provider coverage can be distinguished from a confirmed absence of
  vessels where possible.

### Phase 5: Add best-effort history and vessel trails

#### Objectives

- Store normalized position history independently of the live projection.
- Deliver the first historical product while explicitly treating pre-durability
  history as best-effort.

#### Deliverables

- Append-only, time-partitioned position storage with spatial indexing.
- Idempotent write behavior and explicit out-of-order semantics.
- Configurable raw-position retention.
- Vessel trail query by MMSI and time range.
- Resolution parameter that can simplify long tracks before transfer.
- Map presentation for a selected vessel's path.
- Clear display of source gaps and missing periods.
- Storage-volume, partition-health, and query-latency metrics.
- Retention job exercised in a non-production environment.

#### Exit criteria

- A vessel trail remains correct across duplicate and out-of-order input.
- Users can inspect recent movement without loading raw global history.
- Retention can remove expired raw partitions without blocking ingestion.
- Missing periods are not drawn as continuous travel.
- The product identifies the history as best-effort until Phase 6 completes.

### Phase 6: Introduce durable ingestion and replay

#### Objectives

- Place a durable journal between source receipt and position processing.
- Upgrade new history from best-effort to durable-after-acceptance.

#### Deliverables

- Journal adapter selected through a measured technology evaluation.
- Durable source-envelope append with a documented acceptance guarantee.
- Checkpointed consumer that can stop, restart, and resume.
- Retry policy and poison-message quarantine.
- Operational visibility into append failures, consumer lag, retry counts, and
  oldest unprocessed event age.
- Failure-injection tests for process crashes and downstream outages.
- A recorded durability activation time after which accepted history receives
  the stronger completeness guarantee.

#### Exit criteria

- A process can crash after durable acceptance and recover without losing or
  incorrectly duplicating accepted messages.
- Redis or Postgres outages do not require dropping durably accepted messages.
- Replay produces the same normalized outcome as first-time processing.
- Operational documentation distinguishes provider delivery gaps from internal
  durability failures.

### Phase 7: Operational and scale hardening

#### Objectives

- Make global ingestion and serving recoverable, observable, and economical.

#### Deliverables

- Capacity and failure runbooks.
- Alerts for source gaps, journal append failures, processing lag, projection
  lag, storage growth, and tile error rates.
- Backup and restore exercises for historical storage and configuration.
- Automated load tests for ingestion bursts and hundreds of map users.
- Cost dashboards for journal, database, cache, network egress, and archive.
- Safe deployment and schema migration procedures that do not pause ingestion.

#### Exit criteria

- Recovery objectives are documented and exercised.
- A downstream outage can be absorbed for the agreed duration without data
  loss after durable acceptance.
- Storage and serving costs have explicit budgets and alert thresholds.

### Later: Historical world replay and analytics

Full-world replay is deliberately deferred until live global ingestion, vessel
trails, retention, and clustering are proven. It may require precomputed time
buckets or historical map tiles rather than reconstructing every global vessel
position for every arbitrary timestamp.

Possible later capabilities include:

- Global or regional replay at a historical timestamp.
- Time-window density and traffic-flow analysis.
- Port arrival and departure events.
- Route and behavioral summaries.
- Long-term aggregate datasets after raw-position expiration.

## Migration Strategy

1. Keep the existing AIS consumer and `/live/vessels` path operational while
   introducing stable event identities and idempotent processing.
2. Build the spatial live projection in shadow mode and compare counts, latest
   positions, freshness, and processing lag against the existing Redis
   representation.
3. Introduce spatial map snapshots behind a separate route or feature flag.
4. Move the frontend to viewport-aware snapshots and clusters.
5. Add append-only historical storage and vessel trails, marking the collected
   period as best-effort.
6. Retain the old live route for rollback during an observation window.
7. Insert the durable journal at the established source-processing seam and
   replay into the same historical and live modules.
8. Establish and publish the durability activation time after recovery and
   failure-injection criteria pass.
9. Remove the global-set read path only after correctness and load criteria are
   satisfied.

## Measurement Plan

### Ingestion

- Messages and bytes per second, including peak windows
- Durable append latency and failure rate
- Reconnect frequency and detected source-gap duration
- Duplicate, invalid, out-of-order, and quarantined message rates
- Consumer lag and oldest unprocessed event age

### Storage

- Raw and normalized bytes per day
- Partition creation, retention, and deletion duration
- Historical write throughput
- Live projection vessel count and update throughput
- Replay and projection-rebuild duration

### Serving

- Snapshot and trail latency percentiles
- Cache-hit rate
- Response size by zoom
- Clusters and individual vessels returned per request
- Concurrent request throughput and error rate

### Browser

- Fetch and decode time
- Feature synchronization time
- Render frame time
- Memory usage
- Click hit-detection latency

## Open Questions

### Source and reliability

- Does AISStream explicitly support the required global subscription and volume?
- Does the provider supply sequence identifiers, replay, or gap recovery?
- What reconnect gaps are unavoidable, and how will the product communicate
  them?
- Is a second source adapter eventually required for redundancy or gap filling?
- What source licensing or redistribution restrictions apply to cached tiles and
  historical data?

### Durable ingestion

- Which durable journal implementation meets measured throughput, recovery,
  operational complexity, and cost requirements?
- What replication and flush guarantees define a successful durable append?
- How long must the journal retain acknowledged envelopes for replay?
- What is the stable deduplication identity when source messages lack a unique
  event identifier?
- How much downstream outage time must the journal absorb?

### Historical storage

- How many days of full-fidelity raw positions should remain in primary storage?
- Should original source envelopes use the same retention as normalized
  positions?
- Which downsampling resolutions should be preserved after raw expiration?
- Should expired raw data move to compressed object storage or be deleted?
- How should MMSI reuse and changing vessel identity metadata be represented?
- What is the maximum trail time range exposed to users?

### Live projection and clustering

- Should the spatial live projection use Redis GEO, PostGIS, another spatial
  index, or a measured combination?
- Which stable cell scheme should drive clusters: map tiles, H3, geohashes, or
  database-native grid aggregation?
- At which zoom or density should clusters become individual vessels?
- What individual-marker budget keeps the target browsers responsive?
- Should cluster counts distinguish fresh and stale vessels?
- What is the cache lifetime at world, regional, and harbor zoom levels?
- Should the transport begin as JSON or use vector tiles immediately?

### Product behavior

- How should the map visualize known source outages or poor provider coverage?
- What happens when a user clicks a cluster containing both fresh and stale
  vessels?
- Which trail durations should be offered as presets?
- Should trails show reported points, a simplified line, or both?
- When should full-world historical replay enter the roadmap?

### Capacity and operations

- What exact concurrent-user load should define acceptance within the target of
  hundreds?
- What browser and device classes define the frontend performance floor?
- What latency and availability objectives apply to ingestion, live maps, and
  trails independently?
- What storage and network cost ceilings are acceptable?
- Which failures require paging versus ordinary operational alerts?

## Near-Term Next Steps

1. Run Phase 0 as a time-boxed global-source and capacity investigation.
2. Record provider capability and reliability findings in an architecture
   decision record.
3. Define `SourceEnvelope` and `PositionEvent`, including stable identity,
   deduplication, and out-of-order semantics.
4. Make current position processing idempotent and prove repeatability with
   recorded fixtures.
5. Implement the spatial latest-position projection in shadow mode.
6. Build the smallest map-snapshot slice: query one tile, return either a stable
   cluster or bounded individual vessels, and render it in OpenLayers.
7. Expand viewport querying and frontend clustering under measured global load.
8. Add best-effort append-only history and the first vessel-trail slice.
9. Select and introduce durable ingestion only after the live serving and trail
   paths are functioning and global throughput has been measured.
