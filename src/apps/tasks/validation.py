"""Общие функции нормализации и приведения данных задач."""

from .enums import TaskStatus


def normalize_text(value: object) -> str:
    """Преобразует значение в строку и убирает пробелы по краям."""
    return str(value).strip()


def coerce_task_status(
    value: TaskStatus | str | None,
    *,
    default: TaskStatus,
) -> TaskStatus:
    """Приводит входное значение к TaskStatus с учётом значения по умолчанию."""
    if value is None:
        return default
    if isinstance(value, TaskStatus):
        return value
    return TaskStatus(str(value))
