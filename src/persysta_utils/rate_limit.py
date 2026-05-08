"""Slowapi rate limiter helper.

Wrapper trivial sobre `slowapi.Limiter` com defaults sensatos. Função
existe pra uniformizar o `key_func` entre apps (ambos usam IP do client
como chave default).

Requer `pip install persysta-platform-fastapi-utils[rate-limit]` ou
`slowapi>=0.1.9` instalado separadamente.

Uso típico no app:

    from persysta_utils import build_limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    limiter = build_limiter()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @router.post("/login")
    @limiter.limit("20/minute")
    def login(request: Request, ...):
        ...
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


def build_limiter(
    *,
    key_func: Callable[..., str] | None = None,
    default_limits: list[str] | None = None,
    storage_uri: str | None = None,
    **extra_kwargs: Any,
) -> Any:
    """Constrói `slowapi.Limiter` com `get_remote_address` por default.

    `key_func`: callback que extrai chave do request (default: IP do client).
    `default_limits`: lista de limits aplicados a todos os endpoints
        (ex: `["100/minute"]`). Default: sem limite global.
    `storage_uri`: backend de storage (ex: `"redis://localhost:6379"`).
        Default: in-memory (per-process — OK pra single worker).
    `**extra_kwargs`: passa pro `Limiter.__init__` (escape hatch).

    Returns `slowapi.Limiter` instance.
    """
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    init_kwargs: dict[str, Any] = {"key_func": key_func or get_remote_address}
    if default_limits is not None:
        init_kwargs["default_limits"] = default_limits
    if storage_uri is not None:
        init_kwargs["storage_uri"] = storage_uri

    init_kwargs.update(extra_kwargs)
    return Limiter(**init_kwargs)
