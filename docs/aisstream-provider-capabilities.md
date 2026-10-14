# AISStream provider capabilities

Research date: 2026-10-14

## Confirmed findings

- **Continuous global consumption is the documented usage model.** AISStream describes a persistent connection that clients read continuously, markets the feed as global, and publishes an official example using the whole-world bounding box `[[[-90, -180], [90, 180]]]`. No maximum connection duration is documented. Our probe also received traffic with this subscription. ([homepage](https://www.aisstream.io/), [official README](https://github.com/aisstream/aisstream/blob/main/README.md), [official example](https://github.com/aisstream/example/blob/main/golang/main.go))
- **Connections are limited.** AISStream permits three subscribed connections per account and three open connections per originating IP. The initial subscription must be sent within three seconds, and subscription replacements are limited to one per second. ([documentation](https://www.aisstream.io/documentation/))
- **No numeric compressed-throughput or usage quota is published.** The public materials specify no message-rate cap, compressed-bandwidth cap, daily quota, or bounding-box count/area cap. Uncompressed connections are subject to an unspecified per-user bandwidth limit, with excess messages dropped. ([documentation](https://www.aisstream.io/documentation/))
- **Coverage is described only at a high level.** AISStream says its tracking is powered by a global network of AIS stations, but publishes no coverage map, station inventory, regional guarantees, freshness/completeness target, or statement establishing terrestrial-only versus satellite sources. ([homepage](https://www.aisstream.io/), [documentation](https://www.aisstream.io/documentation/))
- **Delivery is not guaranteed.** AISStream provides no SLA, may drop messages when a client reads too slowly, and recommends reconnecting with exponential backoff and jitter. ([documentation](https://www.aisstream.io/documentation/))
- **There is no durable replay.** Messages missed during a disconnect, provider interruption, or slow-consumer drop cannot be recovered through the documented API. No delivery sequence, resume token, or gap-recovery mechanism is documented. ([documentation](https://www.aisstream.io/documentation/), [message schema](https://github.com/aisstream/ais-message-models/blob/master/type-definition.yaml))
- **Compression matters.** Clients should negotiate `permessage-deflate` and verify it through the subscription confirmation. Probe JSON-byte measurements are not network-wire-byte measurements when compression is active. ([documentation](https://www.aisstream.io/documentation/))
- **Browsers cannot connect directly.** The API key must remain server-side, and client data must be proxied through the application backend. ([documentation](https://www.aisstream.io/documentation/))

Data-use terms are not being investigated further because the current product is non-commercial. Revisit them if the intended use changes.

## Measured so far

On 2026-10-14, a one-hour probe subscribed to global `PositionReport` traffic using one WebSocket connection.

- **284,251 messages** were received: **78.9 messages/second** on average.
- One-second rates were **76 p50**, **114 p95**, **155 p99**, **229 p99.9**, and **243 maximum**.
- The observed peak was **3.08 times** the average rate.
- JSON payload averaged **43.9 KB/second** and **557 bytes/message**.
- **23,177 unique MMSIs** were observed.
- No exact byte-for-byte duplicates were observed within the five-minute duplicate window. This does not measure semantic duplicates whose metadata or timestamps differ.
- **24 position reports** failed structural validation, an invalid rate of **0.0084%**. No invalid JSON, invalid envelopes, or provider-declared invalid positions were observed.
- The longest inter-message gap was **11.2 seconds**, producing ten consecutive complete zero-message seconds. The WebSocket remained connected, so this was a delivery pause rather than an observed disconnect.
- At the observed average, the source would produce approximately **6.82 million messages** and **3.80 GB of decoded JSON payload per day**.

These remain preliminary measurements from one afternoon hour. They cover only `PositionReport` messages. JSON payload bytes are measured after WebSocket decoding and are not network-wire bytes when compression is active. Longer observation is still needed for daily variation and disconnect frequency.

## Consequences

1. A continuously consumed world subscription is supported, but the feed must still be treated as incomplete and best-effort.
2. Do not promise recovery of messages that AISStream fails to deliver.
3. Verify compression and size throughput from measurements because the provider publishes no numeric capacity envelope.
4. Keep AISStream access behind the backend.
