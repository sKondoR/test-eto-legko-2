import re
from dataclasses import dataclass

from app.domain.errors import DomainError

PREFIX = "test_kondrashin_"
_PATTERN = re.compile(re.escape(PREFIX) + r"[a-z0-9_]+")


def is_ours(name: str) -> bool:
    """Кампания из Keitaro наша, если имя начинается с префикса. Остальное не проверяется."""
    return name.startswith(PREFIX)


@dataclass(frozen=True)
class CampaignName:
    value: str

    def __post_init__(self) -> None:
        if not _PATTERN.fullmatch(self.value):
            raise DomainError(
                f"Имя кампании: префикс {PREFIX} и затем латиница в нижнем регистре, цифры или _"
            )

    @classmethod
    def from_suffix(cls, suffix: str) -> "CampaignName":
        return cls(PREFIX + suffix)
