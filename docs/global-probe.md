# Long-running global AIS probe

The probe is isolated from the application backend, database, and Redis. It
connects to AISStream, emits checkpoint records, and writes the same records to
a host-mounted NDJSON capture file.

## One-time setup on the home server

From the repository root:

```sh
mkdir -p captures secrets
printf '%s\n' '<AISSTREAM_API_KEY>' > secrets/aisstream_api_key
chmod 600 secrets/aisstream_api_key
```

The API key is read from the local secret file and is not stored in the
repository or passed through the Compose environment.

## Start the continuous capture

```sh
docker compose \
  -f compose.probe.yaml \
  up -d --build ais-probe
```

`AIS_PROBE_DURATION_SECONDS=0` means run continuously. Checkpoints are written
every minute by default to:

```text
captures/ais-global-probe.ndjson
```

Each received provider frame is also written to a daily raw capture file:

```text
captures/raw/ais-global-raw-YYYY-MM-DD.ndjson
```

The raw capture contains the full decoded AISStream JSON payload, one message
per line. It is separate from the metrics file and is expected to grow by
roughly 3.8 GB per day at the currently observed source rate.

The file is append-only, so choose a new `AIS_PROBE_OUTPUT_FILE` for each
observation run. For example:

```sh
AIS_PROBE_OUTPUT_FILE=ais-global-2026-10-19.ndjson \
docker compose -f compose.probe.yaml up -d --build ais-probe
```

## Monitor and stop

```sh
docker compose -f compose.probe.yaml logs -f ais-probe
docker compose -f compose.probe.yaml ps ais-probe
docker compose -f compose.probe.yaml stop ais-probe
```

Stopping the container preserves all completed checkpoint records. The probe
does not write production state and does not require Postgres or Redis.

## Configuration

The overlay defaults to the whole-world bounding box and `PositionReport`
messages. Override values for a run with environment variables, for example:

```sh
AIS_PROBE_CHECKPOINT_SECONDS=300 \
AIS_PROBE_OUTPUT_FILE=ais-global-7d.ndjson \
docker compose -f compose.probe.yaml up -d --build ais-probe
```

The host must have Docker Compose, network access to AISStream, and enough
disk for the capture. The current measured rate is approximately 3.8 GB/day of
decoded JSON payload before filesystem overhead. Change the raw filename prefix
with `AIS_PROBE_RAW_OUTPUT_PREFIX` if needed.
