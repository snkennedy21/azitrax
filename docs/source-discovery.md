# Source Discovery

This project will use AIS vessel position data as the first live external
source for discovery work.

The first implementation should stream or read vessel positions, prove the
source can support useful map behavior, and keep persistence decisions out of
scope until the payload and update behavior are better understood.

## Source Decision

- Source: AISStream live AIS WebSocket API.
- Endpoint: `wss://stream.aisstream.io/v0/stream`.
- Initial subscription shape: send a JSON subscription message containing an API
  key, one or more bounding boxes, and a `PositionReport` message-type filter.
- Initial geography: keep bounding boxes configurable. If no boxes are supplied,
  use a small development box around New York Harbor:
  `[[[40.4774,-74.2591],[40.9176,-73.7004]]]`.
- Discovery goal: inspect current AIS vessel position messages and decide which
  fields are useful for the frontend experience before designing persistence.

Official reference:

- AISStream API documentation:
  https://aisstream.io/documentation.html

## Authentication

AISStream requires an API key. Keys are created from an authenticated AISStream
account and must be sent in the initial WebSocket subscription message.

The API key must stay on the backend. AISStream does not support browser
cross-origin connections, and its documentation explicitly warns against
exposing API keys in frontend code.

Future source-client code should treat a missing `AISSTREAM_API_KEY` as a reason
to use the fixture source locally, not as an application startup failure.

## Rate Limits And Availability

AISStream is a public beta service and should not be required for normal local
development.

Known constraints to design around:

- The service is beta and provides no uptime SLA.
- WebSocket connections must use `wss`.
- The subscription message must be sent shortly after connecting or the service
  may close the connection.
- Subscriptions should use small bounding boxes during discovery.
- Large subscriptions can produce high message volume; global subscriptions may
  require enough capacity to process hundreds of messages per second.
- Subscription updates may be throttled.
- Invalid API keys and throttling are returned as error messages on the stream.
- AIS coverage depends on terrestrial and satellite receiver availability,
  vessel equipment, and provider coverage, so missing vessels should be
  expected.

## Payload Shape

AISStream sends JSON messages with:

- `MessageType`: AIS message type, such as `PositionReport`.
- `MetaData`: provider metadata including MMSI, vessel name when known,
  latitude, longitude, and UTC receive time.
- `Message`: object keyed by message type. For `PositionReport`, this contains
  AIS position fields.

Important fields for discovery are:

- `MetaData.MMSI`: vessel MMSI.
- `MetaData.ShipName`: vessel name when available.
- `MetaData.latitude` and `MetaData.longitude`: provider-level latest position.
- `MetaData.time_utc`: receive timestamp.
- `Message.PositionReport.UserID`: MMSI from the AIS message body.
- `Message.PositionReport.Latitude` and `Message.PositionReport.Longitude`.
- `Message.PositionReport.Sog`: speed over ground.
- `Message.PositionReport.Cog`: course over ground.
- `Message.PositionReport.TrueHeading`: vessel heading.
- `Message.PositionReport.NavigationalStatus`.
- `Message.PositionReport.PositionAccuracy`.
- `Message.PositionReport.Valid`.

Discovery code may keep this external shape intact at the source boundary. Do
not introduce normalized entities or database tables in this phase.

## Local Fallback

Local development should default to a fixture-backed source so the app can be
developed and tested without network access, AISStream credentials, or live
service availability.

Checked-in fixture:

- `docs/fixtures/aisstream-position-reports-sample.json`

The fixture intentionally mirrors AISStream WebSocket message shape. It is small
enough for tests and UI development, includes multiple vessel position reports,
and uses timestamps that should be treated as sample data rather than current
truth.

Future source-client code should expose at least two modes:

- `AIS_SOURCE=fixture`: read `AIS_FIXTURE_PATH`.
- `AIS_SOURCE=aisstream`: connect to AISStream with `AISSTREAM_API_KEY`.

Recommended behavior:

- Local `.env.example` defaults to `fixture`.
- Tests should use `fixture` unless a test explicitly opts into live network
  behavior.
- Live discovery can switch to `aisstream` with environment variables only.
- If `aisstream` mode receives a network error, timeout, invalid key, throttle
  error, or closed WebSocket, development commands should report the issue
  clearly and may fall back to the fixture when the caller has opted into
  fallback behavior.

## Configuration

The shared configuration keys are listed in `.env.example`:

- `AIS_SOURCE`: `fixture` or `aisstream`.
- `AIS_FIXTURE_PATH`: path to an AISStream-shaped fixture.
- `AIS_ALLOW_FIXTURE_FALLBACK`: whether `aisstream` mode may fall back to the
  fixture after a live-source failure.
- `AISSTREAM_WS_URL`: defaults to `wss://stream.aisstream.io/v0/stream`.
- `AISSTREAM_API_KEY`: optional local API key for live discovery.
- `AISSTREAM_BOUNDING_BOXES`: JSON array of AISStream bounding boxes.
- `AISSTREAM_MESSAGE_TYPES`: comma-separated AIS message types to request.
- `AISSTREAM_CONNECT_TIMEOUT_SECONDS`: WebSocket connection timeout.
- `AISSTREAM_SAMPLE_MESSAGE_LIMIT`: optional cap for discovery commands that
  only need a bounded sample.

These keys are discovery configuration only. They do not imply any persistence
schema.

## Alternatives Considered

AISHub is a possible later adapter because it can return AIS data as JSON, XML,
or CSV over HTTPS. It requires AISHub membership and documents a minimum
one-minute interval between webservice requests, so it is less suitable as the
first live source for an interactive discovery loop.

NOAA MarineCadastre AIS data is useful for historical U.S. AIS analysis and
fixture validation, but it does not provide a live AIS feed. It is not the first
source for live discovery.
