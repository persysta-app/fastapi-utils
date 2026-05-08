"""Tests pra errors.err()."""
from persysta_utils import err


def test_err_basic() -> None:
    assert err("foo_bar") == {"code": "foo_bar"}


def test_err_with_kwargs() -> None:
    assert err("invoice_paid", invoice_id=42, ts="2026-01-01") == {
        "code": "invoice_paid",
        "invoice_id": 42,
        "ts": "2026-01-01",
    }


def test_err_does_not_mutate_kwargs() -> None:
    """err não deve segurar referência ao dict de kwargs."""
    original = {"code": "x", "data": [1, 2, 3]}
    result = err("foo", data=[1, 2, 3])
    assert result is not original
    assert result == {"code": "foo", "data": [1, 2, 3]}


def test_err_code_overrides_kwarg() -> None:
    """Se alguém passa code= como kwarg, conflita com posicional — Python
    levanta TypeError. Garante que API é unambígua."""
    import pytest
    with pytest.raises(TypeError):
        err("a", code="b")  # type: ignore[misc]
