# Backend

FastAPI service for the minimal geospatial app.

## Local Development

Start the backend without the frontend:

```sh
docker compose up --build backend
```

The API will be available at `http://127.0.0.1:8000`.

Check that it is running:

```sh
curl http://127.0.0.1:8000/health
```
