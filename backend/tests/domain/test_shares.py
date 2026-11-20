import pytest

from app.domain.shares import distribute_shares


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (1, [100]),
        (2, [50, 50]),
        (3, [33, 33, 34]),
        (7, [14, 14, 14, 14, 14, 14, 16]),
    ],
)
def test_splits_evenly_with_remainder_on_last(count: int, expected: list[int]) -> None:
    assert distribute_shares(count) == expected


@pytest.mark.parametrize("count", range(1, 101))
def test_shares_always_sum_to_100(count: int) -> None:
    assert sum(distribute_shares(count)) == 100


def test_rejects_empty_offer_list() -> None:
    with pytest.raises(ValueError):
        distribute_shares(0)
