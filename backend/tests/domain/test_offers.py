import pytest

from app.domain.errors import DomainError
from app.domain.offers import OfferSet, OfferShare, diff


def test_evenly_assigns_equal_shares_in_given_order() -> None:
    assert OfferSet.evenly([30, 10, 20]).shares == (
        OfferShare(30, 33),
        OfferShare(10, 33),
        OfferShare(20, 34),
    )


def test_evenly_rejects_empty_list() -> None:
    with pytest.raises(DomainError):
        OfferSet.evenly([])


def test_keeps_manual_shares_from_keitaro() -> None:
    offers = OfferSet((OfferShare(1, 70), OfferShare(2, 30)))
    assert offers.offer_ids == (1, 2)
    assert not offers.is_even


def test_even_split_is_recognized() -> None:
    assert OfferSet.evenly([1, 2, 3]).is_even


def test_rejects_duplicate_offers_naming_the_offer() -> None:
    with pytest.raises(DomainError, match="Оффер 1 указан дважды"):
        OfferSet((OfferShare(1, 50), OfferShare(1, 50)))


@pytest.mark.parametrize("share", [-1, 101])
def test_rejects_share_out_of_range(share: int) -> None:
    with pytest.raises(DomainError):
        OfferSet((OfferShare(1, share),))


def test_diff_lists_added_and_removed_offers() -> None:
    change = diff(OfferSet.evenly([1, 2]), OfferSet.evenly([2, 3, 4]))
    assert change.added == (3, 4)
    assert change.removed == (1,)
    assert change.before == (OfferShare(1, 50), OfferShare(2, 50))
    assert change.after == (OfferShare(2, 33), OfferShare(3, 33), OfferShare(4, 34))


def test_diff_of_identical_sets_is_empty() -> None:
    assert diff(OfferSet.evenly([1, 2]), OfferSet.evenly([1, 2])).is_empty


def test_diff_with_only_reshared_offers_is_not_empty() -> None:
    manual = OfferSet((OfferShare(1, 70), OfferShare(2, 30)))
    change = diff(manual, OfferSet.evenly([1, 2]))
    assert change.added == () and change.removed == ()
    assert not change.is_empty
