class DomainError(ValueError):
    """Нарушено бизнес-правило. Текст сообщения показывается пользователю."""


class KeitaroError(Exception):
    """Keitaro API ответил ошибкой или недоступен. Текст сообщения показывается пользователю."""


class NotFoundError(KeitaroError):
    """Keitaro не нашёл объект: кампанию удалили, отправили в архив или ID неверный."""


class ConflictError(Exception):
    """Поток изменили в Keitaro, пока пользователь его редактировал.

    Текст сообщения показывается пользователю.
    """
