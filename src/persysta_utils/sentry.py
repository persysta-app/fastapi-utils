"""Sentry SDK initialization helper.

No-op safe: `init_sentry(dsn="")` não levanta nem importa sentry-sdk —
permite chamar incondicionalmente em apps sem DSN configurado (modo dev).

Requer `pip install persysta-platform-fastapi-utils[sentry]` ou
`sentry-sdk[fastapi]>=2.0` instalado separadamente.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


def init_sentry(
    dsn: str,
    *,
    environment: str = "development",
    traces_sample_rate: float = 0.05,
    profiles_sample_rate: float = 0.0,
    release: str | None = None,
    before_send: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None] | None = None,
    integrations: list[Any] | None = None,
    send_default_pii: bool = False,
    **extra_kwargs: Any,
) -> bool:
    """Inicializa Sentry SDK. Retorna True se inicializou, False se noop.

    Quando `dsn` é vazio/None, função retorna False sem importar sentry_sdk
    (consumer pode chamar incondicionalmente sem precisar de guard).

    Defaults conservadores:
      - `traces_sample_rate=0.05` (5% das requests pra performance traces)
      - `profiles_sample_rate=0.0` (off — performance profiling consome quota)
      - `send_default_pii=False` (nunca manda IP/headers/cookies; consumer
        opta in se precisar)

    `before_send` recebe `(event, hint)` e retorna event modificado ou None
    pra dropar — use pra redact PII custom (ex: emails em error messages).

    `integrations` aceita lista custom; se None, usa defaults da SDK
    (FastAPI, Starlette, SQLAlchemy auto-detect).

    `**extra_kwargs` passa direto pro `sentry_sdk.init()` — escape hatch pra
    configs avançadas sem a lib precisar conhecer.
    """
    if not dsn:
        return False

    import sentry_sdk

    init_kwargs: dict[str, Any] = {
        "dsn": dsn,
        "environment": environment,
        "traces_sample_rate": traces_sample_rate,
        "profiles_sample_rate": profiles_sample_rate,
        "send_default_pii": send_default_pii,
    }
    if release is not None:
        init_kwargs["release"] = release
    if before_send is not None:
        init_kwargs["before_send"] = before_send
    if integrations is not None:
        init_kwargs["integrations"] = integrations

    init_kwargs.update(extra_kwargs)
    sentry_sdk.init(**init_kwargs)
    return True
