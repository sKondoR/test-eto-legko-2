import pytest

from app.domain.countries import ISO_CODES, CountryCode, parse_countries
from app.domain.errors import DomainError


def test_iso_list_is_complete() -> None:
    assert len(ISO_CODES) == 249


def test_accepts_known_code() -> None:
    assert CountryCode("AU").value == "AU"


@pytest.mark.parametrize("value", ["XX", "au", "AUS", ""])
def test_rejects_unknown_or_unnormalized_code(value: str) -> None:
    with pytest.raises(DomainError):
        CountryCode(value)


def test_parse_normalizes_and_keeps_order() -> None:
    assert parse_countries([" ro", "AU "]) == (CountryCode("RO"), CountryCode("AU"))


def test_parse_drops_duplicates() -> None:
    assert parse_countries(["AU", "au", "RO"]) == (CountryCode("AU"), CountryCode("RO"))


def test_parse_requires_at_least_one_country() -> None:
    with pytest.raises(DomainError):
        parse_countries([" ", ""])


def test_parse_rejects_unknown_code() -> None:
    with pytest.raises(DomainError):
        parse_countries(["AU", "XX"])
