"""Email send — SMTP STARTTLS + SendGrid HTTP API + Brevo HTTP API + BackgroundTasks.

Modos via `cfg.host`:
- `""`                      → dev mode (loga via stdout, retorna dev_logged)
- `"sendgrid-api"`          → SendGrid HTTP API (porta 443)
- `"brevo-api"`             → Brevo HTTP API (porta 443)
- qualquer outro            → SMTP STARTTLS padrão

HTTP providers existem porque alguns hosts (Railway Hobby etc.) bloqueiam
outbound SMTP. HTTP API contorna usando porta 443 com a mesma API key.

Anti-spam headers (Reply-To, List-Unsubscribe, List-Unsubscribe-Post)
são adicionados em TODOS os modos — SMTP e ambos HTTP providers — pra
paridade de deliverability (Gmail/Yahoo penalizam senders sem esses
headers desde 2024).
"""
from __future__ import annotations

import logging
import smtplib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Any

import httpx
from fastapi import BackgroundTasks

from .config import SMTPConfig

# Sentinelas dos providers HTTP API.
SENDGRID_HTTP_HOST = "sendgrid-api"
BREVO_HTTP_HOST = "brevo-api"

log = logging.getLogger(__name__)


@dataclass
class EmailResult:
    """Resultado de envio. `status` ∈ {sent, dev_logged, failed}."""

    status: str
    error_message: str | None = None
    sent_at: datetime | None = None

    @property
    def ok(self) -> bool:
        return self.status in ("sent", "dev_logged")


# Callback assinatura: chamado após envio (sucesso, dev_logged ou falha).
# Permite caller persistir em `email_logs` do schema dele.
OnLogCallback = Callable[[EmailResult, str, str], None]
# args: (result, to_address, subject)


def _resolve_from(cfg: SMTPConfig, fallback_app_name: str = "App") -> str:
    """Resolve From: do cfg ou fallback simples."""
    if cfg.from_addr:
        return cfg.from_addr
    return f"{fallback_app_name} <noreply@example.com>"


def _anti_spam_headers(
    cfg: SMTPConfig,
    *,
    fallback_app_name: str = "App",
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Headers anti-spam padrão + extras do caller.

    - `Reply-To`: usa o From — caso user responda, vai pro suporte.
    - `List-Unsubscribe`: Gmail/Yahoo penalizam senders sem esse header
      desde 2024 (requisito de bulk sender, mesmo em transacional).
    - `List-Unsubscribe-Post`: marca como One-Click Unsubscribe (RFC 8058),
      reduz spam scoring.

    Caller pode sobrepor / adicionar via `extra`.
    """
    from_addr = _resolve_from(cfg, fallback_app_name)
    _, from_email = parseaddr(from_addr)
    headers = {
        "Reply-To": from_addr,
        "List-Unsubscribe": f"<mailto:{from_email}?subject=unsubscribe>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }
    if extra:
        headers.update(extra)
    return headers


def _build_message(
    *,
    cfg: SMTPConfig,
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    extra_headers: dict[str, str] | None,
    fallback_app_name: str,
) -> EmailMessage:
    """Constrói EmailMessage com From/To/Subject + headers anti-spam."""
    msg = EmailMessage()
    msg["From"] = _resolve_from(cfg, fallback_app_name)
    msg["To"] = to
    msg["Subject"] = subject

    for k, v in _anti_spam_headers(cfg, fallback_app_name=fallback_app_name, extra=extra_headers).items():
        msg[k] = v

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    return msg


def _send_via_sendgrid_api(
    cfg: SMTPConfig,
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    *,
    fallback_app_name: str = "App",
    extra_headers: dict[str, str] | None = None,
) -> EmailResult:
    """Envia via SendGrid HTTP API. API key vem do `cfg.password`.

    SendGrid Mail Send API responde 202 em sucesso, 4xx/5xx em erro com
    JSON `{"errors": [{"message": "..."}]}`.
    """
    api_key = cfg.password
    if not api_key:
        return EmailResult(
            status="failed",
            error_message="SendGrid API key missing — preencha o campo password com SG.xxx...",
        )

    from_addr = _resolve_from(cfg, fallback_app_name)
    from_name, from_email = parseaddr(from_addr)
    sender: dict[str, str] = {"email": from_email}
    if from_name:
        sender["name"] = from_name

    headers = _anti_spam_headers(cfg, fallback_app_name=fallback_app_name, extra=extra_headers)

    payload: dict[str, Any] = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": sender,
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
        "headers": headers,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
        if response.status_code in (200, 202):
            return EmailResult(status="sent", sent_at=datetime.now(UTC))
        return EmailResult(
            status="failed",
            error_message=f"HTTP {response.status_code}: {response.text[:300]}",
        )
    except Exception as exc:
        return EmailResult(
            status="failed",
            error_message=f"{type(exc).__name__}: {exc}",
        )


def _send_via_brevo_api(
    cfg: SMTPConfig,
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    *,
    fallback_app_name: str = "App",
    extra_headers: dict[str, str] | None = None,
) -> EmailResult:
    """Envia via Brevo (ex-Sendinblue) HTTP API. API key vem do `cfg.password`.

    Brevo Transactional API responde 201 em sucesso com `{"messageId": "..."}`.
    Erros 4xx/5xx vêm com `{"code": "...", "message": "..."}`.

    Auth via header `api-key` (não Bearer, como SendGrid).
    Endpoint: POST https://api.brevo.com/v3/smtp/email
    Doc: https://developers.brevo.com/reference/sendtransacemail
    """
    api_key = cfg.password
    if not api_key:
        return EmailResult(
            status="failed",
            error_message="Brevo API key missing — preencha o campo password com xkeysib-xxx...",
        )

    from_addr = _resolve_from(cfg, fallback_app_name)
    from_name, from_email = parseaddr(from_addr)
    sender: dict[str, str] = {"email": from_email}
    if from_name:
        sender["name"] = from_name

    headers = _anti_spam_headers(cfg, fallback_app_name=fallback_app_name, extra=extra_headers)

    payload: dict[str, Any] = {
        "sender": sender,
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html_body,
        "textContent": text_body,
        "headers": headers,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": api_key,
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                json=payload,
            )
        # Brevo: 201 Created em sucesso (com messageId no body).
        # Aceita 200 também por defesa — providers às vezes mudam status code.
        if response.status_code in (200, 201, 202):
            return EmailResult(status="sent", sent_at=datetime.now(UTC))
        return EmailResult(
            status="failed",
            error_message=f"HTTP {response.status_code}: {response.text[:300]}",
        )
    except Exception as exc:
        return EmailResult(
            status="failed",
            error_message=f"{type(exc).__name__}: {exc}",
        )


def _send_via_smtp(
    cfg: SMTPConfig,
    msg: EmailMessage,
    to: str,
) -> EmailResult:
    """Envia via SMTP STARTTLS. Falha = `EmailResult(status='failed', error=...)`."""
    try:
        with smtplib.SMTP(cfg.host, cfg.port, timeout=15) as smtp:
            if cfg.tls:
                smtp.starttls()
            if cfg.user:
                smtp.login(cfg.user, cfg.password)
            smtp.send_message(msg)
        return EmailResult(status="sent", sent_at=datetime.now(UTC))
    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {exc}"
        log.error("[EMAIL ERROR] Failed to send to %s: %s", to, err_msg)
        return EmailResult(status="failed", error_message=err_msg)


def _do_send(
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    cfg: SMTPConfig,
    extra_headers: dict[str, str] | None,
    fallback_app_name: str,
    on_log: OnLogCallback | None,
) -> EmailResult:
    """Worker síncrono — envio + chamada ao callback de log."""
    if not cfg.host:
        log.info("[EMAIL DEV MODE] to=%s subject=%s\n%s", to, subject, text_body)
        result = EmailResult(status="dev_logged", sent_at=datetime.now(UTC))
    elif cfg.host == SENDGRID_HTTP_HOST:
        result = _send_via_sendgrid_api(
            cfg, to, subject, html_body, text_body,
            fallback_app_name=fallback_app_name, extra_headers=extra_headers,
        )
    elif cfg.host == BREVO_HTTP_HOST:
        result = _send_via_brevo_api(
            cfg, to, subject, html_body, text_body,
            fallback_app_name=fallback_app_name, extra_headers=extra_headers,
        )
    else:
        msg = _build_message(
            cfg=cfg,
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            extra_headers=extra_headers,
            fallback_app_name=fallback_app_name,
        )
        result = _send_via_smtp(cfg, msg, to)

    if on_log is not None:
        try:
            on_log(result, to, subject)
        except Exception as log_exc:
            log.error("[EMAIL ERROR] on_log callback failed: %s", log_exc)

    return result


def send_email(
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    cfg: SMTPConfig,
    extra_headers: dict[str, str] | None = None,
    fallback_app_name: str = "App",
    background_tasks: BackgroundTasks | None = None,
    on_log: OnLogCallback | None = None,
) -> EmailResult:
    """Envia email transacional. Retorna `EmailResult` (status + error_message).

    Modo dual:
      - `cfg.host == ""` → dev mode (loga, retorna `dev_logged`).
      - `cfg.host == SENDGRID_HTTP_HOST` (`"sendgrid-api"`) → SendGrid HTTP API (porta 443).
      - `cfg.host == BREVO_HTTP_HOST` (`"brevo-api"`) → Brevo HTTP API (porta 443).
      - outro `cfg.host` → SMTP STARTTLS padrão (porta `cfg.port`).

    Async: passe `background_tasks` (FastAPI). Worker roda DEPOIS do
    response sair, latência da request cai pra ~10ms. Resultado retornado
    é stub (`status="sent"` antecipado — verificação real fica em
    `on_log`). Use modo blocking (sem `background_tasks`) quando UI
    precisa do feedback (ex: test email da config admin).

    `on_log(result, to, subject)`: callback invocado após cada envio
    (sucesso ou falha). Caller usa pra persistir em `email_logs` do schema
    dele. Exceptions no callback são engolidas (logging-de-logging não
    pode quebrar fluxo).
    """
    if background_tasks is not None:
        # Async path: agenda task; retorna stub. on_log roda depois.
        background_tasks.add_task(
            _do_send,
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            cfg=cfg,
            extra_headers=extra_headers,
            fallback_app_name=fallback_app_name,
            on_log=on_log,
        )
        return EmailResult(status="sent", sent_at=datetime.now(UTC))

    return _do_send(
        to=to,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        cfg=cfg,
        extra_headers=extra_headers,
        fallback_app_name=fallback_app_name,
        on_log=on_log,
    )
