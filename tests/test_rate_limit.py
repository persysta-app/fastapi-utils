"""Tests pra rate_limit.build_limiter()."""
from persysta_utils import build_limiter


def test_build_limiter_returns_slowapi_limiter() -> None:
    from slowapi import Limiter

    limiter = build_limiter()
    assert isinstance(limiter, Limiter)


def test_build_limiter_uses_get_remote_address_by_default() -> None:
    """Default key_func deve ser get_remote_address (extrai IP do client)."""
    from slowapi.util import get_remote_address

    limiter = build_limiter()
    assert limiter._key_func is get_remote_address


def test_build_limiter_accepts_custom_key_func() -> None:
    custom_key: object = lambda req: "custom"  # noqa: E731
    limiter = build_limiter(key_func=custom_key)  # type: ignore[arg-type]
    assert limiter._key_func is custom_key


def test_build_limiter_accepts_default_limits() -> None:
    limiter = build_limiter(default_limits=["100/minute"])
    # slowapi armazena defaults internamente; vamos só confirmar que não crasha
    # e que o atributo existe
    assert hasattr(limiter, "_default_limits")
