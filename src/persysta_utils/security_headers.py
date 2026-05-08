"""Security headers middleware.

Adiciona headers HTTP de segurança em TODAS as responses:
- `X-Content-Type-Options: nosniff` — bloqueia MIME sniffing
- `X-Frame-Options: DENY` — previne clickjacking via iframe
- `Referrer-Policy: strict-origin-when-cross-origin` — limita leak de URL
- `Permissions-Policy: camera=(), microphone=(), ...` — limita APIs sensíveis
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` — HSTS
  (apenas quando `is_production=True`)

Uso:

    from persysta_utils import add_security_headers_middleware

    app = FastAPI()
    add_security_headers_middleware(
        app,
        is_production=lambda: settings.ENVIRONMENT == "production",
    )

Override de defaults:

    add_security_headers_middleware(
        app,
        is_production=...,
        permissions_policy="camera=(), microphone=(), geolocation=(self)",
        extra_headers={"Cross-Origin-Opener-Policy": "same-origin"},
    )
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

DEFAULT_PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(self)"
)
DEFAULT_HSTS_MAX_AGE = 31536000  # 1 year


def add_security_headers_middleware(
    app: Any,
    *,
    is_production: Callable[[], bool] = lambda: False,
    permissions_policy: str = DEFAULT_PERMISSIONS_POLICY,
    hsts_max_age_seconds: int = DEFAULT_HSTS_MAX_AGE,
    hsts_include_subdomains: bool = True,
    extra_headers: dict[str, str] | None = None,
) -> None:
    """Registra middleware HTTP que injeta security headers em todas as
    responses.

    Args:
        app: FastAPI app instance.
        is_production: callback que decide se HSTS é injetado. Default
            sempre False (dev-friendly — HSTS em dev pode quebrar HTTP).
        permissions_policy: valor do header `Permissions-Policy`.
        hsts_max_age_seconds: max-age do HSTS quando ativo.
        hsts_include_subdomains: se True, HSTS aplica a subdomains.
        extra_headers: dict adicional (`Cross-Origin-Opener-Policy`, etc.)
            sobrepostos aos defaults.
    """

    @app.middleware("http")
    async def security_headers(
        request: Any,
        call_next: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = permissions_policy

        if is_production():
            hsts_value = f"max-age={hsts_max_age_seconds}"
            if hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            response.headers["Strict-Transport-Security"] = hsts_value

        if extra_headers:
            for k, v in extra_headers.items():
                response.headers[k] = v

        return response
