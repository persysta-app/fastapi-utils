"""Email transactional service — SMTP STARTTLS + SendGrid HTTP API fallback.

Modo dual:
  - SMTP padrão (STARTTLS) — funciona com Gmail App Password, AWS SES,
    SendGrid SMTP, qualquer MTA RFC-compliant.
  - SendGrid HTTP API (host == `SENDGRID_HTTP_HOST`) — usa porta 443 em vez
    de 587, contorna provedores que bloqueiam outbound SMTP (Railway Hobby,
    alguns container envs).
  - Dev mode (host vazio) — loga subject + body via `logging`, retorna
    sucesso. Permite testar fluxo end-to-end sem MTA.

Async: `send_email(..., background_tasks=bt)` agenda o SMTP send pra rodar
DEPOIS do response sair (FastAPI BackgroundTasks). Latência da request cai
de ~3-5s pra ~10ms. Pra envios "blocking" (test SMTP da config UI), não
passe `background_tasks` — chamada vira síncrona e retorna o resultado.

A lib NÃO escreve em `email_logs` da app — caller passa callback `on_log`
pra registrar no schema dele (Persysta usa `to_address`, Vinon usa
`to_email`; cada um tem seu modelo).
"""
from .config import SMTPConfig
from .service import (
    SENDGRID_HTTP_HOST,
    EmailResult,
    OnLogCallback,
    send_email,
)

__all__ = [
    "SENDGRID_HTTP_HOST",
    "EmailResult",
    "OnLogCallback",
    "SMTPConfig",
    "send_email",
]
