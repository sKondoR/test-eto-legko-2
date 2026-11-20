from app.domain.errors import DomainError

NO_OFFERS = "В потоке должен быть хотя бы один оффер"


def distribute_shares(count: int) -> list[int]:
    """Делит 100% трафика поровну между офферами; остаток деления получает последний."""
    if count < 1:
        raise DomainError(NO_OFFERS)
    base = 100 // count
    return [base] * (count - 1) + [100 - base * (count - 1)]
