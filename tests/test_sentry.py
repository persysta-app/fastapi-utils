"""Tests pra sentry.init_sentry()."""
from unittest.mock import MagicMock, patch

from persysta_utils import init_sentry


def test_init_sentry_noop_when_dsn_empty() -> None:
    """Sem DSN, função retorna False sem importar sentry_sdk."""
    assert init_sentry("") is False
    assert init_sentry(None) is False  # type: ignore[arg-type]


def test_init_sentry_calls_sdk_when_dsn_present() -> None:
    with patch("sentry_sdk.init") as mock_init:
        result = init_sentry(
            "https://abc@example.ingest.sentry.io/123",
            environment="production",
            traces_sample_rate=0.1,
            release="myapp@1.0.0",
        )
    assert result is True
    mock_init.assert_called_once()
    kwargs = mock_init.call_args.kwargs
    assert kwargs["dsn"] == "https://abc@example.ingest.sentry.io/123"
    assert kwargs["environment"] == "production"
    assert kwargs["traces_sample_rate"] == 0.1
    assert kwargs["release"] == "myapp@1.0.0"


def test_init_sentry_passes_before_send() -> None:
    cb = MagicMock()
    with patch("sentry_sdk.init") as mock_init:
        init_sentry("dsn://x", before_send=cb)
    assert mock_init.call_args.kwargs["before_send"] is cb


def test_init_sentry_extra_kwargs_pass_through() -> None:
    """Escape hatch: kwargs desconhecidos são repassados pro sentry_sdk.init."""
    with patch("sentry_sdk.init") as mock_init:
        init_sentry("dsn://x", server_name="my-server", auto_enabling_integrations=True)
    kwargs = mock_init.call_args.kwargs
    assert kwargs["server_name"] == "my-server"
    assert kwargs["auto_enabling_integrations"] is True


def test_init_sentry_default_pii_off() -> None:
    """Default conservador: send_default_pii=False (não vaza IP/cookies)."""
    with patch("sentry_sdk.init") as mock_init:
        init_sentry("dsn://x")
    assert mock_init.call_args.kwargs["send_default_pii"] is False
