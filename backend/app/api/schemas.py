"""Формы запросов и ответов /api. По ним генерируются TS-типы (pnpm gen:api)."""

from datetime import datetime

from pydantic import BaseModel


class ErrorOut(BaseModel):
    detail: str


class ConfigOut(BaseModel):
    name_prefix: str
    default_geo: list[str]
    countries: list[str]


class OfferOut(BaseModel):
    id: int
    name: str


class CampaignOut(BaseModel):
    id: int
    name: str


class CampaignCreateIn(BaseModel):
    name_suffix: str
    countries: list[str]
    offer_id: int


class CampaignCreatedOut(BaseModel):
    id: int


class OfferShareModel(BaseModel):
    offer_id: int
    share: int


class HistoryEntryOut(BaseModel):
    changed_at: datetime
    before: list[OfferShareModel]
    after: list[OfferShareModel]
    added: list[int]
    removed: list[int]


class EditorOut(BaseModel):
    id: int
    name: str
    geo: list[str]
    offers: list[OfferShareModel]
    disabled_offer_ids: list[int]
    # False — доли ручные или часть офферов выключена в Keitaro: интерфейс предупреждает.
    is_even: bool
    history: list[HistoryEntryOut]


class OffersSaveIn(BaseModel):
    # Офферы, которые редактор показал пользователю: по ним сервер ловит чужую правку (409).
    expected: list[OfferShareModel]
    offer_ids: list[int]


class OffersSavedOut(BaseModel):
    offers: list[OfferShareModel]
