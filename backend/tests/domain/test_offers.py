import pytest

from app.domain.errors import DomainError
from app.domain.offers import OfferSet, OfferShare, diff, is_even_split


def shares(*pairs: tuple[int, int]) -> tuple[OfferShare, ...]:
    return tuple(OfferShare(offer_id, share) for offer_id, share in pairs)


# OfferSet — то, что сохраняем в Keitaro: строгие правила.


def test_evenly_assigns_equal_shares_in_given_order() -> None:
    assert OfferSet.evenly([30, 10, 20]).shares == shares((30, 33), (10, 33), (20, 34))


def test_evenly_rejects_empty_list() -> None:
    with pytest.raises(DomainError):
        OfferSet.evenly([])


def test_rejects_duplicate_offers_naming_the_offer() -> None:
    with pytest.raises(DomainError, match="Оффер 1 указан дважды"):
        OfferSet(shares((1, 50), (1, 50)))


@pytest.mark.parametrize("share", [-1, 101])
def test_rejects_share_out_of_range(share: int) -> None:
    with pytest.raises(DomainError):
        OfferSet(shares((1, share)))


def test_rejects_shares_not_summing_to_100() -> None:
    with pytest.raises(DomainError):
        OfferSet(shares((1, 10)))


def test_accepts_manual_split_summing_to_100() -> None:
    assert OfferSet(shares((1, 70), (2, 30))).offer_ids == (1, 2)


# Прочитанное из Keitaro — как есть, без проверок.


def test_even_split_is_recognized() -> None:
    assert is_even_split(shares((1, 33), (2, 33), (3, 34)))


def test_even_split_with_remainder_elsewhere_is_still_even() -> None:
    assert is_even_split(shares((1, 34), (2, 33), (3, 33)))


@pytest.mark.parametrize(
    "current",
    [
        shares((1, 70), (2, 30)),
        shares(),
        shares((1, 50), (1, 50)),
        tuple(OfferShare(i, 0) for i in range(101)),
    ],
)
def test_manual_or_broken_split_is_not_even(current: tuple[OfferShare, ...]) -> None:
    assert not is_even_split(current)


def test_diff_lists_added_and_removed_offers() -> None:
    change = diff(shares((1, 50), (2, 50)), OfferSet.evenly([2, 3, 4]))
    assert change.added == (3, 4)
    assert change.removed == (1,)
    assert change.before == shares((1, 50), (2, 50))
    assert change.after == shares((2, 33), (3, 33), (4, 34))


def test_diff_of_identical_sets_is_empty() -> None:
    assert diff(shares((1, 50), (2, 50)), OfferSet.evenly([1, 2])).is_empty


def test_diff_with_only_reshared_offers_is_not_empty() -> None:
    change = diff(shares((1, 70), (2, 30)), OfferSet.evenly([1, 2]))
    assert change.added == () and change.removed == ()
    assert not change.is_empty


def test_diff_repairs_broken_keitaro_flow() -> None:
    change = diff(shares((1, 50), (1, 50)), OfferSet.evenly([1]))
    assert change.removed == ()
    assert change.after == shares((1, 100))
    assert diff(shares(), OfferSet.evenly([7])).added == (7,)
