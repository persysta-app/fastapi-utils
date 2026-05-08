"""Email transactional service — SMTP + SendGrid HTTP API + Brevo HTTP API.

Modo dual via `SMTPConfig.host`:
  - SMTP padrão (STARTTLS) — funciona com Gmail App Password, AWS SES,
    SendGrid SMTP, Brevo SMTP, qualquer MTA RFC-compliant.
  - SendGrid HTTP API (host == `SENDGRID_HTTP_HOST`) — porta 443.
  - Brevo HTTP API (host == `BREVO_HTTP_HOST`) — porta 443.
  - Dev mode (host vazio) — loga via stdout, retorna sucesso.

HTTP providers existem porque alguns hosts (Railway Hobby etc.) bloqueiam
outbound SMTP. HTTP API contorna usando porta 443.

Async: `send_email(..., background_tasks=bt)` agenda o send pra rodar
DEPOIS do response sair (FastAPI BackgroundTasks).

A lib NÃO escreve em `email_logs` da app — caller passa callback `on_log`
pra registrar no schema dele.
"""
from .config import SMTPConfig
from .service import (
    BREVO_HTTP_HOST,
    SENDGRID_HTTP_HOST,
    EmailResult,
    OnLogCallback,
    send_email,
)

__all__ = [
    "SENDGRID_HTTP_HOST",
    "BREVO_HTTP_HOST",
    "EmailResult",
    "OnLogCallback",
    "SMTPConfig",
    "send_email",
]
