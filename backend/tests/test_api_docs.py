from fastapi.testclient import TestClient

from app.main import create_app


def test_api_docs_are_enabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("API_DOCS_ENABLED", raising=False)
    client = TestClient(create_app())

    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_api_docs_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("API_DOCS_ENABLED", "false")
    client = TestClient(create_app())

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
