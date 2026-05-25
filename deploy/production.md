# Production Environment

Production is intended to run behind Cloudflare Tunnel:

```text
Cloudflare -> cloudflared -> nginx -> backend
```

The `backend`, `db`, `redis`, and `ais-consumer` services are private Docker
network services. The production Compose stack does not publish host ports for
them.

## Required variables

Set these values in an uncommitted local `.env` file or another secret source
before running `compose.prod.yaml`:

```sh
CLOUDFLARED_TUNNEL_TOKEN=<Cloudflare Tunnel token>
AISSTREAM_API_KEY=<AISStream API key>
POSTGRES_PASSWORD=<production database password>
FRONTEND_ORIGINS=https://<public app hostname>
```

`FRONTEND_ORIGINS` is used by the backend CORS middleware. In production it
should be the public frontend origin only, for example:

```sh
FRONTEND_ORIGINS=https://vector.example.com
```

Do not commit production secrets, tunnel tokens, API tokens, database passwords,
or generated credential files.

## Production defaults

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
