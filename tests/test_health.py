"""Tests pra build_health_router."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from persysta_utils import build_health_router


def test_default_liveness_returns_ok() -> None:
    app = FastAPI()
    app.include_router(build_health_router())
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_liveness_includes_app_name_and_version() -> None:
    app = FastAPI()
    app.include_router(build_health_router(app_name="myapp", app_version="1.2.3"))
    client = TestClient(app)

    r = client.get("/health")
    body = r.json()
    assert body["status"] == "ok"
    assert body["app"] == "myapp"
    assert body["version"] == "1.2.3"


def test_readiness_no_checks_returns_ok() -> None:
    app = FastAPI()
    app.include_router(build_health_router())
    client = TestClient(app)

    r = client.get("/readyz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"] == {}


def test_readiness_all_checks_pass() -> None:
    app = FastAPI()
    app.include_router(build_health_router(readiness_checks={
        "db": lambda: (True, "ok"),
        "smtp": lambda: (True, "configured"),
    }))
    client = TestClient(app)

    r = client.get("/readyz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"]["db"] == {"status": "ok", "message": "ok"}
    assert body["checks"]["smtp"] == {"status": "ok", "message": "configured"}


def test_readiness_one_check_fails_returns_503() -> None:
    app = FastAPI()
    app.include_router(build_health_router(readiness_checks={
        "db": lambda: (True, "ok"),
        "smtp": lambda: (False, "host not configured"),
    }))
    client = TestClient(app)

    r = client.get("/readyz")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["checks"]["db"]["status"] == "ok"
    assert body["checks"]["smtp"]["status"] == "fail"
    assert body["checks"]["smtp"]["message"] == "host not configured"


def test_readiness_check_exception_treated_as_fail() -> None:
    """Check que levanta exception não pode quebrar readiness."""
    def broken():
        raise RuntimeError("boom")

    app = FastAPI()
    app.include_router(build_health_router(readiness_checks={"x": broken}))
    client = TestClient(app)

    r = client.get("/readyz")
    assert r.status_code == 503
    assert r.json()["checks"]["x"]["status"] == "fail"
    assert "RuntimeError" in r.json()["checks"]["x"]["message"]


def test_can_disable_liveness() -> None:
    app = FastAPI()
    app.include_router(build_health_router(include_liveness=False))
    client = TestClient(app)

    assert client.get("/health").status_code == 404
    assert client.get("/readyz").status_code == 200


def test_custom_paths() -> None:
    app = FastAPI()
    app.include_router(build_health_router(
        liveness_path="/livez",
        readiness_path="/ready",
    ))
    client = TestClient(app)

    assert client.get("/livez").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/health").status_code == 404
