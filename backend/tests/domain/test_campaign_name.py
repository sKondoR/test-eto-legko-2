import pytest

from app.domain.campaign_name import CampaignName, is_ours
from app.domain.errors import DomainError


def test_builds_name_from_suffix() -> None:
    assert CampaignName.from_suffix("campaign1").value == "test_kondrashin_campaign1"


def test_accepts_full_name_with_prefix() -> None:
    assert CampaignName("test_kondrashin_au_1").value == "test_kondrashin_au_1"


@pytest.mark.parametrize(
    "value",
    [
        "campaign1",  # нет префикса
        "test_kondrashin_",  # пустой суффикс
        "test_kondrashin_Camp",  # заглавные
        "test_kondrashin_кампания",  # кириллица
        "test_kondrashin_a-b",  # дефис
        "test_kondrashin_a b",  # пробел
    ],
)
def test_rejects_invalid_names(value: str) -> None:
    with pytest.raises(DomainError):
        CampaignName(value)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("test_kondrashin_c1", True),
        ("test_kondrashin_Hand Edited", True),  # переименовали вручную — всё равно наша
        ("test_ivanov_c1", False),
        ("kondrashin_c1", False),
    ],
)
def test_is_ours_checks_prefix_only(name: str, expected: bool) -> None:
    assert is_ours(name) is expected
