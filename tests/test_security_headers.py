"""Tests pra add_security_headers_middleware."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from persysta_utils import add_security_headers_middleware


def _build_app(**kwargs) -> FastAPI:
    app = FastAPI()
    add_security_headers_middleware(app, **kwargs)

    @app.get("/")
    def root():
        return {"ok": True}

    return app


def test_default_headers_present_in_dev() -> None:
    client = TestClient(_build_app())
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in r.headers["Permissions-Policy"]
    # HSTS NOT present em dev mode
    assert "Strict-Transport-Security" not in r.headers


def test_hsts_present_in_production() -> None:
    client = TestClient(_build_app(is_production=lambda: True))
    r = client.get("/")
    hsts = r.headers["Strict-Transport-Security"]
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts


def test_hsts_can_disable_subdomains() -> None:
    client = TestClient(_build_app(
        is_production=lambda: True,
        hsts_include_subdomains=False,
    ))
    r = client.get("/")
    hsts = r.headers["Strict-Transport-Security"]
    assert "includeSubDomains" not in hsts


def test_custom_permissions_policy() -> None:
    custom = "camera=(self), microphone=(), geolocation=(self)"
    client = TestClient(_build_app(permissions_policy=custom))
    r = client.get("/")
    assert r.headers["Permissions-Policy"] == custom


def test_extra_headers_merged() -> None:
    client = TestClient(_build_app(extra_headers={
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Embedder-Policy": "require-corp",
    }))
    r = client.get("/")
    assert r.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert r.headers["Cross-Origin-Embedder-Policy"] == "require-corp"


def test_extra_headers_override_defaults() -> None:
    """Extra headers podem sobrepor defaults (ex: X-Frame-Options ALLOWALL)."""
    client = TestClient(_build_app(extra_headers={
        "X-Frame-Options": "SAMEORIGIN",
    }))
    r = client.get("/")
    assert r.headers["X-Frame-Options"] == "SAMEORIGIN"


def test_custom_hsts_max_age() -> None:
    client = TestClient(_build_app(
        is_production=lambda: True,
        hsts_max_age_seconds=86400,  # 1 day
    ))
    r = client.get("/")
    assert "max-age=86400" in r.headers["Strict-Transport-Security"]
