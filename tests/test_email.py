"""Tests pra email.send_email() — modos dev / SMTP / SendGrid HTTP."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from persysta_utils.email import (
    SENDGRID_HTTP_HOST,
    EmailResult,
    SMTPConfig,
    send_email,
)


def test_dev_mode_returns_dev_logged() -> None:
    """Sem host configurado, retorna dev_logged sem tentar conexão."""
    cfg = SMTPConfig(host="", from_addr="App <noreply@x.com>")
    result = send_email(
        to="user@x.com",
        subject="hi",
        html_body="<p>hi</p>",
        text_body="hi",
        cfg=cfg,
    )
    assert result.status == "dev_logged"
    assert result.error_message is None
    assert result.ok is True


def test_dev_mode_calls_on_log_callback() -> None:
    cfg = SMTPConfig(host="")
    cb = MagicMock()
    send_email(
        to="user@x.com",
        subject="hi",
        html_body="<p>hi</p>",
        text_body="hi",
        cfg=cfg,
        on_log=cb,
    )
    cb.assert_called_once()
    result_arg, to_arg, subject_arg = cb.call_args.args
    assert result_arg.status == "dev_logged"
    assert to_arg == "user@x.com"
    assert subject_arg == "hi"


def test_on_log_exception_does_not_break_send() -> None:
    """Exception no callback não quebra envio."""
    cfg = SMTPConfig(host="")
    cb = MagicMock(side_effect=RuntimeError("boom"))
    result = send_email(
        to="user@x.com",
        subject="hi",
        html_body="<p>hi</p>",
        text_body="hi",
        cfg=cfg,
        on_log=cb,
    )
    assert result.status == "dev_logged"


def test_smtp_mode_calls_starttls_and_sends() -> None:
    """SMTP path: STARTTLS + login + send_message."""
    cfg = SMTPConfig(host="smtp.example.com", port=587, user="u", password="p", tls=True)
    fake_smtp = MagicMock()
    with patch("smtplib.SMTP") as smtp_class:
        smtp_class.return_value.__enter__.return_value = fake_smtp
        result = send_email(
            to="user@x.com",
            subject="hi",
            html_body="<p>hi</p>",
            text_body="hi",
            cfg=cfg,
        )
    assert result.status == "sent"
    smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=15)
    fake_smtp.starttls.assert_called_once()
    fake_smtp.login.assert_called_once_with("u", "p")
    fake_smtp.send_message.assert_called_once()


def test_smtp_mode_without_user_skips_login() -> None:
    cfg = SMTPConfig(host="smtp.example.com", user="", password="", tls=False)
    fake_smtp = MagicMock()
    with patch("smtplib.SMTP") as smtp_class:
        smtp_class.return_value.__enter__.return_value = fake_smtp
        send_email(
            to="user@x.com", subject="hi", html_body="<p>hi</p>",
            text_body="hi", cfg=cfg,
        )
    fake_smtp.starttls.assert_not_called()
    fake_smtp.login.assert_not_called()
    fake_smtp.send_message.assert_called_once()


def test_smtp_failure_returns_failed_status() -> None:
    cfg = SMTPConfig(host="smtp.example.com", user="u", password="p")
    with patch("smtplib.SMTP", side_effect=ConnectionError("network down")):
        result = send_email(
            to="user@x.com", subject="hi", html_body="<p>hi</p>",
            text_body="hi", cfg=cfg,
        )
    assert result.status == "failed"
    assert "ConnectionError" in (result.error_message or "")
    assert result.ok is False


def test_sendgrid_http_mode_posts_to_api() -> None:
    cfg = SMTPConfig(host=SENDGRID_HTTP_HOST, password="SG.test_api_key", from_addr="App <noreply@x.com>")
    response = MagicMock(status_code=202, text="")
    with patch("httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.post.return_value = response
        result = send_email(
            to="user@x.com", subject="hi", html_body="<p>hi</p>",
            text_body="hi", cfg=cfg,
        )
    assert result.status == "sent"
    post_args = client_class.return_value.__enter__.return_value.post.call_args
    assert post_args.args[0] == "https://api.sendgrid.com/v3/mail/send"
    assert post_args.kwargs["headers"]["Authorization"] == "Bearer SG.test_api_key"
    assert post_args.kwargs["json"]["personalizations"][0]["to"][0]["email"] == "user@x.com"


def test_sendgrid_http_mode_4xx_returns_failed() -> None:
    cfg = SMTPConfig(host=SENDGRID_HTTP_HOST, password="SG.bad")
    response = MagicMock(status_code=401, text='{"errors":[{"message":"invalid api key"}]}')
    with patch("httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.post.return_value = response
        result = send_email(
            to="user@x.com", subject="hi", html_body="<p>hi</p>",
            text_body="hi", cfg=cfg,
        )
    assert result.status == "failed"
    assert "401" in (result.error_message or "")


def test_sendgrid_http_mode_no_api_key_fails() -> None:
    cfg = SMTPConfig(host=SENDGRID_HTTP_HOST, password="")
    result = send_email(
        to="user@x.com", subject="hi", html_body="<p>hi</p>",
        text_body="hi", cfg=cfg,
    )
    assert result.status == "failed"
    assert "API key" in (result.error_message or "")


def test_sendgrid_http_mode_network_error_returns_failed() -> None:
    cfg = SMTPConfig(host=SENDGRID_HTTP_HOST, password="SG.x")
    with patch("httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("dns fail")
        result = send_email(
            to="user@x.com", subject="hi", html_body="<p>hi</p>",
            text_body="hi", cfg=cfg,
        )
    assert result.status == "failed"
    assert "ConnectError" in (result.error_message or "")


def test_anti_spam_headers_applied_in_smtp_mode() -> None:
    """Reply-To + List-Unsubscribe + List-Unsubscribe-Post devem estar presentes."""
    cfg = SMTPConfig(host="smtp.example.com", from_addr="App <noreply@x.com>", tls=False)
    captured_msg = []

    fake_smtp = MagicMock()
    fake_smtp.send_message.side_effect = lambda msg: captured_msg.append(msg)

    with patch("smtplib.SMTP") as smtp_class:
        smtp_class.return_value.__enter__.return_value = fake_smtp
        send_email(
            to="user@x.com", subject="hi", html_body="<p>hi</p>",
            text_body="hi", cfg=cfg,
        )

    assert len(captured_msg) == 1
    msg = captured_msg[0]
    assert msg["Reply-To"] == "App <noreply@x.com>"
    assert "noreply@x.com" in msg["List-Unsubscribe"]
    assert msg["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


def test_extra_headers_merged() -> None:
    cfg = SMTPConfig(host="smtp.example.com", from_addr="x@x.com", tls=False)
    captured_msg: list[object] = []
    fake_smtp = MagicMock()
    fake_smtp.send_message.side_effect = lambda m: captured_msg.append(m)
    with patch("smtplib.SMTP") as smtp_class:
        smtp_class.return_value.__enter__.return_value = fake_smtp
        send_email(
            to="user@x.com", subject="hi", html_body="<p>hi</p>",
            text_body="hi", cfg=cfg,
            extra_headers={"X-Custom-Tag": "marketing-q1"},
        )
    msg = captured_msg[0]
    assert msg["X-Custom-Tag"] == "marketing-q1"  # type: ignore[index]


def test_background_tasks_returns_immediately_and_schedules() -> None:
    """Quando background_tasks passado, retorna stub `sent` sem executar SMTP."""
    cfg = SMTPConfig(host="smtp.example.com", user="u", password="p")
    bg = MagicMock()

    with patch("smtplib.SMTP") as smtp_class:
        result = send_email(
            to="user@x.com", subject="hi", html_body="<p>hi</p>",
            text_body="hi", cfg=cfg,
            background_tasks=bg,
        )

    # SMTP não foi chamado — task foi agendada
    smtp_class.assert_not_called()
    bg.add_task.assert_called_once()
    assert result.status == "sent"


@pytest.mark.parametrize("status,ok", [
    ("sent", True),
    ("dev_logged", True),
    ("failed", False),
])
def test_email_result_ok_property(status: str, ok: bool) -> None:
    assert EmailResult(status=status).ok is ok
