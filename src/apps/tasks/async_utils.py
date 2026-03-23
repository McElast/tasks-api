"""Общие async-хелперы для задач."""

from collections.abc import Callable
from typing import Any

from asgiref.sync import sync_to_async
from django.contrib.auth.models import User


def assert_user(user: object, *, context: str) -> User:
    """Гарантирует, что объект является django.contrib.auth User."""
    if not isinstance(user, User):
        raise TypeError(f'{context} must contain django.contrib.auth User.')
    return user


async def run_sync[T](func: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Выполняет sync-функцию из async-контекста."""
    return await sync_to_async(func)(*args, **kwargs)
