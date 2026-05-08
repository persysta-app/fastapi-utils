"""SMTP / SendGrid HTTP config dataclass."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SMTPConfig:
    """Config pra envio de email.

    `host` vazio → modo dev (loga, não envia).
    `host == "sendgrid-api"` → modo SendGrid HTTP API (sentinela; valor real
        no `persysta_utils.email.SENDGRID_HTTP_HOST`).
    Qualquer outro `host` → SMTP STARTTLS padrão.

    `password` é plain text — caller é responsável por descriptografar
    (Fernet ou similar) antes de chamar `send_email`. A lib NÃO armazena
    nem persiste credenciais.
    """

    host: str
    port: int = 587
    user: str = ""
    password: str = ""
    tls: bool = True
    from_addr: str = ""
