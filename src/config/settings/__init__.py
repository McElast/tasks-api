"""Пакет настроек Django-проекта."""

from types import ModuleType
from typing import Any


def apply_module_settings(target: dict[str, Any], source: ModuleType) -> None:
    """Копирует настройки в верхнем регистре из исходного модуля."""
    target.update({name: getattr(source, name) for name in dir(source) if name.isupper()})
