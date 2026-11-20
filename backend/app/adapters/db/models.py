from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CampaignRow(Base):
    """Попытка создать кампанию через приложение: удачная или нет."""

    __tablename__ = "campaigns"
    __table_args__ = (CheckConstraint("status IN ('created', 'failed')", name="status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # None — Keitaro не успел создать кампанию.
    keitaro_id: Mapped[int | None] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(255))
    geo: Mapped[list[str]] = mapped_column(ARRAY(String(2)))
    offer_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OfferChangeRow(Base):
    """Правка офферов в редакторе. Внешнего ключа на campaigns нет: редактор открывает
    и кампании test_kondrashin_*, созданные вне приложения."""

    __tablename__ = "offer_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_id: Mapped[int] = mapped_column(index=True)
    before: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    after: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    added: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    removed: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
