"""SQLAlchemy 2.x mixins for cross-cutting fields.

Para ser usado com `class Foo(TimestampMixin, SoftDeleteMixin, Base): ...`.

Não inclui mixins multi-tenant (`AccountScopedMixin`) ou audit user-tracking
(`AuditMixin` com `created_by`/`updated_by` FKs) — esses são app-specific
e ficam no consumer (Persysta tem ambos; Vinon não usa).
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adiciona `created_at` + `updated_at` automáticos.

    `created_at`: setado uma vez no INSERT via `func.now()` (server-side, evita
    drift entre app + DB clocks).
    `updated_at`: setado no INSERT e em todo UPDATE via `onupdate`.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SoftDeleteMixin:
    """Soft delete uniforme: `deleted_at IS NULL` = ativo.

    Use sempre que delete deva preservar histórico (audit, FKs, restore).
    Hard delete só via job de purge (LGPD) ou admin explícito.

    Queries de listagem precisam filtrar `WHERE deleted_at IS NULL`
    explicitamente — SQLAlchemy 2.x não tem global filter built-in seguro
    em multi-tenant; melhor explícito que mágico.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
