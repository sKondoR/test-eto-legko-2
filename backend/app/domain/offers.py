from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.errors import DomainError
from app.domain.shares import NO_OFFERS, distribute_shares


@dataclass(frozen=True)
class OfferShare:
    offer_id: int
    share: int


@dataclass(frozen=True)
class OfferSet:
    """Офферы потока с долями трафика. Порядок важен: остаток деления у последнего."""

    shares: tuple[OfferShare, ...]

    def __post_init__(self) -> None:
        if not self.shares:
            raise DomainError(NO_OFFERS)
        if len(set(self.offer_ids)) != len(self.shares):
            raise DomainError("Оффер уже есть в потоке")

    @classmethod
    def evenly(cls, offer_ids: Sequence[int]) -> "OfferSet":
        shares = distribute_shares(len(offer_ids))
        return cls(tuple(OfferShare(i, s) for i, s in zip(offer_ids, shares, strict=True)))

    @property
    def offer_ids(self) -> tuple[int, ...]:
        return tuple(s.offer_id for s in self.shares)

    @property
    def is_even(self) -> bool:
        return [s.share for s in self.shares] == distribute_shares(len(self.shares))


@dataclass(frozen=True)
class OfferChange:
    before: tuple[OfferShare, ...]
    after: tuple[OfferShare, ...]
    added: tuple[int, ...]
    removed: tuple[int, ...]

    @property
    def is_empty(self) -> bool:
        return self.before == self.after


def diff(before: OfferSet, after: OfferSet) -> OfferChange:
    return OfferChange(
        before=before.shares,
        after=after.shares,
        added=tuple(i for i in after.offer_ids if i not in before.offer_ids),
        removed=tuple(i for i in before.offer_ids if i not in after.offer_ids),
    )
