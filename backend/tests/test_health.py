def test_app_starts_and_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_system_status_shape(client):
    r = client.get("/api/system/status")
    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "ok"
    assert body["database"]["status"] == "ok"
    assert body["vector_store"]["status"] == "ok"
    assert "reachable" in body["ollama"]
    assert body["embeddings"]["backend"] == "hash"


def test_swagger_docs_available(client):
    assert client.get("/docs").status_code == 200
