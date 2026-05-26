# Production Deploy and Smoke Test

This is the first production deployment flow for running Azitrax on one machine
with Docker Compose and Cloudflare Tunnel.

Production ingress is:

```text
public browser
  -> Cloudflare
  -> cloudflared
  -> nginx
      /api/* -> backend:8000
      /      -> static frontend build
```

`nginx` is the production application gateway and is built from
deployment-focused files under `deploy/nginx/`. The Vite dev server is not part
of production. `backend`, `ais-consumer`, `db`, and `redis` are private Docker
network services and do not publish host ports.

## Prerequisites

On the production mini PC:

- Docker Engine or Docker Desktop with the Docker Compose plugin.
- Git access to this repository.
- `curl` for smoke tests.
- Outbound HTTPS and DNS access. No inbound router port forwarding is required.
- A Cloudflare account with a domain or subdomain for the app.
- An AISStream API key.
- Enough local disk for Docker images and the PostGIS Docker volume.

## Required Environment

Create an uncommitted `.env` file on the production host:

```sh
CLOUDFLARED_TUNNEL_TOKEN=<Cloudflare Tunnel token>
AISSTREAM_API_KEY=<AISStream API key>
POSTGRES_PASSWORD=<production database password>
FRONTEND_ORIGINS=https://<public app hostname>
```

`FRONTEND_ORIGINS` is used by the backend CORS middleware. In production it
should be the public frontend origin only, for example:

```sh
FRONTEND_ORIGINS=https://azitrax.com
```

Do not commit production secrets, tunnel tokens, API tokens, database passwords,
or generated Cloudflare credential files.

`compose.prod.yaml` defaults new production Compose projects and databases to
`azitrax`. If this host already has a PostGIS volume initialized with the old
`vector` project, database, or user names, keep temporary `.env` overrides
pointing at those old names until you migrate, or create the `azitrax`
database/user and move the data before removing those compatibility overrides.

## Cloudflare Tunnel

Create or attach a remotely managed Cloudflare Tunnel:

1. In Cloudflare, create a tunnel for this app.
2. Choose the Docker connector setup and copy the tunnel token.
3. Put that token in `.env` as `CLOUDFLARED_TUNNEL_TOKEN`.
4. Add a public hostname route for the production hostname.
5. Set the route service URL to:

```text
http://nginx:80
```

Cloudflare terminates public TLS. The `cloudflared` container opens an outbound
tunnel and forwards requests to private nginx over the Docker network.

See `deploy/cloudflared/README.md` for the focused tunnel credential notes.

## Start, Stop, and Inspect

Start the production stack:

```sh
docker compose -f compose.prod.yaml up -d --build
```

Inspect service state:

```sh
docker compose -f compose.prod.yaml ps
```

Follow logs:

```sh
docker compose -f compose.prod.yaml logs -f
```

Follow one service:

```sh
docker compose -f compose.prod.yaml logs -f cloudflared
docker compose -f compose.prod.yaml logs -f nginx
docker compose -f compose.prod.yaml logs -f backend
docker compose -f compose.prod.yaml logs -f ais-consumer
```

Stop the stack without deleting the PostGIS volume:

```sh
docker compose -f compose.prod.yaml down
```

## Smoke Test

Set a shell variable for the public hostname:

```sh
APP_ORIGIN=https://azitrax.com
```

Replace the value with the hostname configured in Cloudflare.

### Frontend Static Serving

Check that Cloudflare reaches nginx and nginx serves the built frontend:

```sh
curl -I "$APP_ORIGIN/"
```

Expected result:

- HTTP status is `200`.
- Response headers include nginx.
- No Vite dev server port is involved.

Fetch the first page body:

```sh
curl -fsS "$APP_ORIGIN/" | head
```

Expected result: an HTML document for the frontend app.

### Backend API Routing

Check that browser-style `/api/*` requests route through nginx to FastAPI:

```sh
curl -fsS "$APP_ORIGIN/api/health"
```

Expected result:

```json
{"status":"ok"}
```

Check database and Redis connectivity through the same ingress path:

```sh
curl -fsS "$APP_ORIGIN/api/health/db"
curl -fsS "$APP_ORIGIN/api/health/redis"
```

Expected result: both return `status: ok`. The database health response also
includes the PostGIS version.

### Startup Migrations

Backend startup runs Flyway migrations before serving requests. Verify from
logs:

```sh
docker compose -f compose.prod.yaml logs backend | grep -E "Database migrations completed successfully|Flyway"
```

Verify from PostGIS:

```sh
docker compose -f compose.prod.yaml exec db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT installed_rank, version, description, success FROM flyway_schema_history ORDER BY installed_rank;"'
```

Expected result: migration rows exist and `success` is true.

### AIS Consumer and Redis Live State

Check that the consumer is running:

```sh
docker compose -f compose.prod.yaml ps ais-consumer
docker compose -f compose.prod.yaml logs ais-consumer --tail=100
```

Inspect the AIS source status written to Redis:

```sh
docker compose -f compose.prod.yaml exec redis redis-cli GET live:ais:status
```

Expected result: JSON with `source` set to `aisstream` and a status such as
`connecting`, `connected`, or `reconnecting`.

Check the live vessel index:

```sh
docker compose -f compose.prod.yaml exec redis redis-cli SCARD live:vessels
```

Then check the API snapshot through nginx:

```sh
curl -fsS "$APP_ORIGIN/api/live/vessels"
```

Expected result: JSON with `items` and `metadata`. `items` may be empty until
AISStream sends renderable messages inside the configured bounding box, but
`metadata.source_status` should reflect the consumer state.

## Production Defaults

The production stack sets:

```sh
AIS_SOURCE=aisstream
AIS_ALLOW_FIXTURE_FALLBACK=false
REDIS_URL=redis://redis:6379/0
VITE_API_BASE_URL=/api
```

Redis is private to the Docker network and ephemeral. PostGIS data is stored in
the Docker-managed `postgres_data` volume.

Database pool settings use the existing application defaults unless overridden:

```sh
POSTGRES_CONNECT_TIMEOUT=5
POSTGRES_POOL_MIN_SIZE=1
POSTGRES_POOL_MAX_SIZE=5
POSTGRES_POOL_TIMEOUT=5
```

## Troubleshooting

Missing tunnel credentials:

```text
CLOUDFLARED_TUNNEL_TOKEN is required
```

Add `CLOUDFLARED_TUNNEL_TOKEN` to the uncommitted `.env` file. In Cloudflare,
confirm the public hostname route points to `http://nginx:80`.

Missing AISStream API key:

```text
AISSTREAM_API_KEY is required
```

Add `AISSTREAM_API_KEY` to `.env`, then restart `ais-consumer`.

Backend startup failures:

```sh
docker compose -f compose.prod.yaml logs backend
docker compose -f compose.prod.yaml ps db redis
```

Look for migration errors, missing Postgres variables, or unhealthy `db` and
`redis` services.

Empty live vessel snapshots:

- Check `docker compose -f compose.prod.yaml logs ais-consumer --tail=100`.
- Check `docker compose -f compose.prod.yaml exec redis redis-cli GET live:ais:status`.
- Confirm `AISSTREAM_BOUNDING_BOXES` covers the expected area.
- Confirm AISStream is returning `PositionReport` messages.
- Empty `items` can be normal before the first renderable vessel message.

## Non-Production Omissions

The production stack intentionally does not include:

- pgAdmin.
- Test database initialization.
- Vite dev server.
- Public host ports for backend, PostGIS, or Redis.
- CI/CD automation.
- Backup or restore automation.
- Alerting or centralized logging.
- Host provisioning automation.
