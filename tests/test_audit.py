"""Tests pra audit log helper + mixin."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from persysta_utils import AuditLogMixin, log_action


class Base(DeclarativeBase):
    pass


class AuditLogEntry(AuditLogMixin, Base):
    __tablename__ = "audit_log"


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_log_action_creates_entry(session: Session) -> None:
    log_action(
        session,
        AuditLogEntry,
        actor_id=42,
        action="customer.approve",
        resource="user",
        resource_id="123",
        meta={"approved_by": "admin@x.com"},
    )
    session.commit()

    entry = session.query(AuditLogEntry).first()
    assert entry is not None
    assert entry.actor_id == 42
    assert entry.action == "customer.approve"
    assert entry.resource == "user"
    assert entry.resource_id == "123"
    assert entry.meta == {"approved_by": "admin@x.com"}
    assert entry.created_at is not None


def test_log_action_extracts_request_metadata(session: Session) -> None:
    """Quando `request` é passado, extrai IP + user_agent."""
    fake_request = MagicMock()
    fake_request.client.host = "203.0.113.42"
    fake_request.headers = {"user-agent": "Mozilla/5.0 (test browser)"}

    log_action(
        session,
        AuditLogEntry,
        actor_id=1,
        action="x.y",
        request=fake_request,
    )
    session.commit()

    entry = session.query(AuditLogEntry).first()
    assert entry.ip_address == "203.0.113.42"
    assert entry.user_agent == "Mozilla/5.0 (test browser)"


def test_log_action_truncates_long_user_agent(session: Session) -> None:
    long_ua = "A" * 1000
    fake_request = MagicMock()
    fake_request.client.host = "1.2.3.4"
    fake_request.headers = {"user-agent": long_ua}

    log_action(session, AuditLogEntry, action="x", request=fake_request)
    session.commit()

    entry = session.query(AuditLogEntry).first()
    assert entry.user_agent is not None
    assert len(entry.user_agent) == 500


def test_log_action_handles_missing_request(session: Session) -> None:
    log_action(session, AuditLogEntry, action="x.y", actor_id=1)
    session.commit()

    entry = session.query(AuditLogEntry).first()
    assert entry.ip_address is None
    assert entry.user_agent is None


def test_log_action_anonymous_actor(session: Session) -> None:
    """actor_id=None permitido (ações de sistema/anônimas)."""
    log_action(session, AuditLogEntry, action="cron.cleanup")
    session.commit()

    entry = session.query(AuditLogEntry).first()
    assert entry.actor_id is None
    assert entry.action == "cron.cleanup"


def test_log_action_swallows_exceptions(session: Session) -> None:
    """Audit log NÃO pode quebrar fluxo de negócio."""

    # Simula erro dando model inválido (atributo missing)
    class Broken:
        def __init__(self, **kwargs):
            raise RuntimeError("bad model")

    # Não deve raise
    log_action(session, Broken, action="x")
    # Log foi engolido (warning silencioso) — fluxo continua


def test_audit_log_mixin_has_canonical_fields(session: Session) -> None:
    """Smoke test: criar entry direto sem o helper."""
    e = AuditLogEntry(
        actor_id=1,
        action="x.y",
        resource="r",
        resource_id="42",
        ip_address="1.2.3.4",
        user_agent="ua",
        meta={"k": "v"},
        created_at=datetime.now(UTC),
    )
    session.add(e)
    session.commit()
    session.refresh(e)
    assert e.id is not None
    assert e.action == "x.y"
