"""Формы запросов и ответов /api. По ним генерируются TS-типы (pnpm gen:api).

Простые доменные dataclass (OfferShare, OfferSummary, CampaignSummary) pydantic отдаёт
как есть, поэтому здесь только формы, которых в домене нет.
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.offers import OfferShare


class ErrorOut(BaseModel):
    detail: str


class ConfigOut(BaseModel):
    name_prefix: str
    default_geo: list[str]
    countries: list[str]


class CampaignCreateIn(BaseModel):
    name_suffix: str
    countries: list[str]
    offer_id: int


class CampaignCreatedOut(BaseModel):
    id: int


class HistoryEntryOut(BaseModel):
    changed_at: datetime
    before: list[OfferShare]
    after: list[OfferShare]
    added: list[int]
    removed: list[int]


class EditorOut(BaseModel):
    id: int
    name: str
    geo: list[str]
    offers: list[OfferShare]
    disabled_offer_ids: list[int]
    is_even: bool  # см. EditorView.is_even
    history: list[HistoryEntryOut]


class OffersSaveIn(BaseModel):
    # Офферы, которые редактор показал пользователю: по ним сервер ловит чужую правку (409).
    expected: list[OfferShare]
    offer_ids: list[int]


class OffersSavedOut(BaseModel):
    offers: list[OfferShare]
