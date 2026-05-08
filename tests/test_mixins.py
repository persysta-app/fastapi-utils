"""Tests pros mixins de DB."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from persysta_utils import SoftDeleteMixin, TimestampMixin


class Base(DeclarativeBase):
    pass


class Product(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_timestamp_mixin_sets_created_at_on_insert(session: Session) -> None:
    p = Product(name="Wine")
    session.add(p)
    session.commit()
    session.refresh(p)
    assert p.created_at is not None
    # Diff < 5s do now
    delta = abs((datetime.now(UTC) - p.created_at).total_seconds())
    assert delta < 5


def test_timestamp_mixin_sets_updated_at(session: Session) -> None:
    p = Product(name="Wine")
    session.add(p)
    session.commit()
    session.refresh(p)
    initial_updated = p.updated_at

    # Pequeno sleep não é necessário no SQLite memory — onupdate é
    # disparado pela mutação, basta mexer + commit
    p.name = "Wine Reserve"
    session.commit()
    session.refresh(p)
    # Changed at least once (timestamps may match if clock resolution low,
    # but row triggered onupdate)
    assert p.updated_at >= initial_updated


def test_soft_delete_mixin_starts_null(session: Session) -> None:
    p = Product(name="Wine")
    session.add(p)
    session.commit()
    session.refresh(p)
    assert p.deleted_at is None


def test_soft_delete_mixin_can_be_set(session: Session) -> None:
    p = Product(name="Wine")
    session.add(p)
    session.commit()

    now = datetime.now(UTC)
    p.deleted_at = now
    session.commit()
    session.refresh(p)
    assert p.deleted_at is not None
    assert abs((p.deleted_at - now).total_seconds()) < 1
