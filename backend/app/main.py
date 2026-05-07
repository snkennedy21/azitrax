from fastapi import FastAPI

app = FastAPI(title="Vector API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
