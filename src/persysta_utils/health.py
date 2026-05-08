"""Health check helpers.

Retorna handlers FastAPI prontos pra `/health` (liveness) e `/readyz`
(readiness com checks customizados).

Uso simples — só liveness:

    from persysta_utils import build_health_router

    app = FastAPI()
    app.include_router(build_health_router())

Com readiness checks (DB ping, SMTP, etc.):

    def check_db() -> tuple[bool, str]:
        try:
            with SessionLocal() as s:
                s.execute(text("SELECT 1"))
            return True, "ok"
        except Exception as e:
            return False, f"db error: {e}"


    def check_smtp() -> tuple[bool, str]:
        return bool(settings.SMTP_HOST), "ok" if settings.SMTP_HOST else "not configured"


    app.include_router(build_health_router(
        readiness_checks={"db": check_db, "smtp": check_smtp},
    ))

Endpoints expostos:
- `GET /health` — sempre 200 com `{"status": "ok"}`. Liveness probe.
- `GET /readyz` — 200 se TODOS os checks pass; 503 se algum falhar. Body
  inclui status de cada check.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Check signature: retorna (ok, message). False ok = unhealthy.
HealthCheck = Callable[[], tuple[bool, str]]


def build_health_router(
    *,
    liveness_path: str = "/health",
    readiness_path: str = "/readyz",
    readiness_checks: dict[str, HealthCheck] | None = None,
    include_liveness: bool = True,
    include_readiness: bool = True,
    app_name: str | None = None,
    app_version: str | None = None,
) -> APIRouter:
    """Constrói APIRouter com endpoints de health.

    Args:
        liveness_path: path do liveness endpoint (default `/health`).
        readiness_path: path do readiness endpoint (default `/readyz`).
        readiness_checks: dict `{name: check_fn}`. Cada check_fn retorna
            `(ok, msg)`. Default: nenhum (readiness só responde {"status": "ok"}).
        include_liveness: se True, registra liveness endpoint.
        include_readiness: se True, registra readiness endpoint.
        app_name, app_version: incluídos no body do liveness pra debugging.

    Returns: `APIRouter` pronto pra `app.include_router(...)`.
    """
    router = APIRouter(tags=["health"])

    if include_liveness:
        @router.get(liveness_path)
        def liveness() -> dict[str, str | None]:
            payload: dict[str, str | None] = {"status": "ok"}
            if app_name:
                payload["app"] = app_name
            if app_version:
                payload["version"] = app_version
            return payload

    if include_readiness:
        checks = readiness_checks or {}

        @router.get(readiness_path)
        def readiness() -> JSONResponse:
            results: dict[str, dict[str, str]] = {}
            all_ok = True
            for name, check_fn in checks.items():
                try:
                    ok, msg = check_fn()
                except Exception as e:
                    ok, msg = False, f"check raised: {type(e).__name__}: {e}"
                results[name] = {"status": "ok" if ok else "fail", "message": msg}
                if not ok:
                    all_ok = False

            status_code = 200 if all_ok else 503
            return JSONResponse(
                status_code=status_code,
                content={
                    "status": "ok" if all_ok else "degraded",
                    "checks": results,
                },
            )

    return router
