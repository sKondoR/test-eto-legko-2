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
    """Офферы потока, которые сохраняем в Keitaro. Порядок важен: остаток у последнего.

    Состояние, прочитанное из Keitaro, сюда не оборачивается: его правили вручную,
    и оно может нарушать правила. Оно живёт как tuple[OfferShare, ...].
    """

    shares: tuple[OfferShare, ...]

    def __post_init__(self) -> None:
        if not self.shares:
            raise DomainError(NO_OFFERS)
        seen: set[int] = set()
        for s in self.shares:
            if s.offer_id in seen:
                raise DomainError(f"Оффер {s.offer_id} указан дважды")
            if not 0 <= s.share <= 100:
                raise DomainError(f"Доля оффера {s.offer_id} вне диапазона 0–100%: {s.share}")
            seen.add(s.offer_id)
        if sum(s.share for s in self.shares) != 100:
            raise DomainError("Сумма долей офферов должна быть 100%")

    @classmethod
    def evenly(cls, offer_ids: Sequence[int]) -> "OfferSet":
        shares = distribute_shares(len(offer_ids))
        return cls(tuple(OfferShare(i, s) for i, s in zip(offer_ids, shares, strict=True)))

    @property
    def offer_ids(self) -> tuple[int, ...]:
        return tuple(s.offer_id for s in self.shares)


def is_even_split(shares: Sequence[OfferShare]) -> bool:
    """Доли из Keitaro поделены поровну (остаток может стоять у любого оффера).

    False — доли ручные или поток сломан: интерфейс предупреждает, что сохранение их перезапишет.
    """
    if not 1 <= len(shares) <= 100 or len({s.offer_id for s in shares}) != len(shares):
        return False
    return sorted(s.share for s in shares) == sorted(distribute_shares(len(shares)))


@dataclass(frozen=True)
class OfferChange:
    before: tuple[OfferShare, ...]
    after: tuple[OfferShare, ...]
    added: tuple[int, ...]
    removed: tuple[int, ...]

    @property
    def is_empty(self) -> bool:
        return self.before == self.after


def diff(before: Sequence[OfferShare], after: Sequence[OfferShare]) -> OfferChange:
    """before — как было в Keitaro (любое), after — что сохранили (OfferSet.shares).

    after не проверяется: история читает его из БД, и смена правил OfferSet не должна её ломать.
    """
    before_ids = [s.offer_id for s in before]
    after_ids = [s.offer_id for s in after]
    return OfferChange(
        before=tuple(before),
        after=tuple(after),
        added=tuple(i for i in after_ids if i not in before_ids),
        removed=tuple(dict.fromkeys(i for i in before_ids if i not in after_ids)),
    )
