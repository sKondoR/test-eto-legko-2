def distribute_shares(count: int) -> list[int]:
    """Делит 100% трафика поровну между офферами; остаток деления получает последний."""
    if count < 1:
        raise ValueError("В потоке должен быть хотя бы один оффер")
    base = 100 // count
    return [base] * (count - 1) + [100 - base * (count - 1)]
