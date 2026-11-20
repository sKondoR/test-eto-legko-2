"""Таблицы журнала: попытки создать кампанию и правки офферов в редакторе."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.campaign_name import MAX_LENGTH


class Base(DeclarativeBase):
    pass


class CampaignRow(Base):
    """Попытка создать кампанию через приложение: удачная или нет."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    # None — Keitaro не успел создать кампанию.
    keitaro_id: Mapped[int | None]
    name: Mapped[str] = mapped_column(String(MAX_LENGTH))
    geo: Mapped[list[str]] = mapped_column(ARRAY(String(2)))
    offer_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    status: Mapped[str] = mapped_column(String(16))  # created | failed
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OfferChangeRow(Base):
    """Правка офферов в редакторе: доли до и после, [{"offer_id", "share"}].

    Внешнего ключа на campaigns нет: редактор открывает и кампании test_kondrashin_*,
    созданные вне приложения. Добавленные и удалённые офферы вычисляются из before/after.
    """

    __tablename__ = "offer_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_id: Mapped[int] = mapped_column(index=True)
    before: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    after: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
