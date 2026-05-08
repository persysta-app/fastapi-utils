"""Audit log helper + mixin.

Padrão pra registrar ações de mutação (create/update/delete) em endpoints
admin/sensitive. Útil pra compliance LGPD, debugging "quem fez o quê",
investigation pós-incidente.

Uso típico:

    from persysta_utils import AuditLogMixin, log_action

    # 1. Model concreto:
    class AuditLogEntry(AuditLogMixin, Base):
        __tablename__ = "audit_log"

    # 2. Em endpoints admin:
    log_action(
        db,
        AuditLogEntry,
        actor_id=current_user.id,
        action="customer.approve",
        resource="user",
        resource_id=str(target_user.id),
        request=request,  # extrai IP + user_agent
        meta={"approved_by": current_user.email, "previous_status": "pending"},
    )

A função engole exceções (audit não pode quebrar fluxo de negócio) — só
loga warning. `flush()` interno garante que a row vai pro DB no commit
do caller (sem `commit()` interno — caller decide a transaction
boundary).

Mixin tem campos canônicos:
- `id`: PK
- `actor_id`: user que fez (FK opcional — caller define)
- `action`: string ASCII identificadora (`customer.approve`,
  `coupon.delete`, etc.)
- `resource`: tipo de entidade afetada (`user`, `order`, `product`)
- `resource_id`: ID da entidade (string pra suportar UUID/composite)
- `ip_address`, `user_agent`: do request (preenchidos por log_action)
- `meta`: JSON com contexto adicional
- `created_at`: timestamp
"""
from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, Session, mapped_column

log = logging.getLogger(__name__)


class AuditLogMixin:
    """Campos canônicos pra tabela de audit log.

    Caller cria seu model concreto (`__tablename__`, FKs Customizados):

        class AuditLogEntry(AuditLogMixin, Base):
            __tablename__ = "audit_log"
            # Opcional: FK pra user
            # actor_id = mapped_column(ForeignKey("users.id"), nullable=True)

    Mixin não declara FKs porque cada app tem seu nome de tabela `users`
    + comportamento de cascade. Caller pode override `actor_id` se quiser
    FK explícita.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )


def log_action(
    db: Session,
    model: type[Any],
    *,
    actor_id: int | None = None,
    action: str,
    resource: str | None = None,
    resource_id: str | None = None,
    request: Any = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Registra uma entrada de audit log. Best-effort — exceção engolida.

    Args:
        db: Session ativa.
        model: classe concreta do model que herda `AuditLogMixin` (a lib
            não conhece o `__tablename__` do consumer).
        actor_id: user que fez a ação. None = anônimo / sistema.
        action: identificador da ação. Convenção: `<dominio>.<verbo>`
            em snake_case (`customer.approve`, `coupon.delete`).
        resource: tipo de entidade afetada (`user`, `order`).
        resource_id: ID da entidade. String pra suportar UUID + composite.
        request: FastAPI Request (opcional). Se passado, extrai
            `client.host` e `headers.user-agent` automaticamente.
        meta: contexto adicional (dict serializável JSON).

    Não faz commit — caller controla transaction boundary. Use
    `db.flush()` internamente pra garantir que row vai junto com o
    commit do caller.
    """
    ip = None
    ua = None
    if request is not None:
        with contextlib.suppress(Exception):
            ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent")

    try:
        entry = model(
            actor_id=actor_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip,
            user_agent=ua[:500] if ua else None,
            meta=meta,
            created_at=datetime.now(UTC),
        )
        db.add(entry)
        db.flush()
    except Exception as exc:
        log.warning("audit log failed for action=%s: %r", action, exc)
        with contextlib.suppress(Exception):
            db.rollback()
