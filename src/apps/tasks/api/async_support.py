"""Вспомогательные типы и функции для async-совместимого APIView."""

from collections.abc import Callable, Coroutine
from inspect import iscoroutinefunction
from typing import Any, Protocol, TypeIs

from django.contrib.auth.models import AnonymousUser, User
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView as DRFAPIView

type RequestUser = User | AnonymousUser
type AuthResult = tuple[Any, Any] | None
type SyncAuthenticate = Callable[[Request], AuthResult]
type AsyncAuthenticate = Callable[[Request], Coroutine[Any, Any, AuthResult]]
type SyncHandler = Callable[..., Response]
type AsyncHandler = Callable[..., Coroutine[Any, Any, Response]]
type MaybeUserFactory = Callable[[], object] | object | None
type MaybeTokenFactory = Callable[[], object] | object | None


class SyncPermissionCheck(Protocol):
    """Permission c синхронной проверкой общего доступа."""

    def has_permission(self, request: Request, view: DRFAPIView) -> bool:
        """Проверяет общий доступ к view."""
        ...


class AsyncPermissionCheck(Protocol):
    """Permission c асинхронной проверкой общего доступа."""

    def has_permission(self, request: Request, view: DRFAPIView) -> Coroutine[Any, Any, bool]:
        """Проверяет общий доступ к view асинхронно."""
        ...


class SyncObjectPermissionCheck(Protocol):
    """Permission c синхронной объектной проверкой."""

    def has_object_permission(self, request: Request, view: DRFAPIView, obj: Any) -> bool:
        """Проверяет доступ к конкретному объекту."""
        ...


class AsyncObjectPermissionCheck(Protocol):
    """Permission c асинхронной объектной проверкой."""

    def has_object_permission(self, request: Request, view: DRFAPIView, obj: Any) -> Coroutine[Any, Any, bool]:
        """Проверяет доступ к конкретному объекту асинхронно."""
        ...


class SyncThrottleCheck(Protocol):
    """Throttle c синхронной проверкой запроса."""

    def allow_request(self, request: Request, view: DRFAPIView) -> bool:
        """Решает, можно ли пропустить запрос."""
        ...

    def wait(self) -> float | None:
        """Возвращает время ожидания до следующей попытки."""
        ...


class AsyncThrottleCheck(Protocol):
    """Throttle c асинхронной проверкой запроса."""

    def allow_request(self, request: Request, view: DRFAPIView) -> Coroutine[Any, Any, bool]:
        """Решает, можно ли пропустить запрос асинхронно."""
        ...

    def wait(self) -> float | None:
        """Возвращает время ожидания до следующей попытки."""
        ...


def is_async_authenticate(authenticate: SyncAuthenticate | AsyncAuthenticate) -> TypeIs[AsyncAuthenticate]:
    """Проверяет, что authenticator использует async authenticate."""
    return iscoroutinefunction(authenticate)


def is_async_handler(handler: SyncHandler | AsyncHandler) -> TypeIs[AsyncHandler]:
    """Проверяет, что HTTP handler асинхронный."""
    return iscoroutinefunction(handler)


def has_async_permission(
    permission: SyncPermissionCheck | AsyncPermissionCheck,
) -> TypeIs[AsyncPermissionCheck]:
    """Проверяет, что permission.has_permission является async."""
    return iscoroutinefunction(permission.has_permission)


def has_async_object_permission(
    permission: SyncObjectPermissionCheck | AsyncObjectPermissionCheck,
) -> TypeIs[AsyncObjectPermissionCheck]:
    """Проверяет, что permission.has_object_permission является async."""
    return iscoroutinefunction(permission.has_object_permission)


def has_async_throttle(
    throttle: SyncThrottleCheck | AsyncThrottleCheck,
) -> TypeIs[AsyncThrottleCheck]:
    """Проверяет, что throttle.allow_request является async."""
    return iscoroutinefunction(throttle.allow_request)


def resolve_unauthenticated_user(factory: MaybeUserFactory) -> RequestUser:
    """Возвращает пользователя по настройке UNAUTHENTICATED_USER."""
    if not callable(factory):
        return AnonymousUser()

    unauthenticated_user = factory()
    if isinstance(unauthenticated_user, User | AnonymousUser):
        return unauthenticated_user
    raise TypeError('UNAUTHENTICATED_USER must return User or AnonymousUser.')


def resolve_unauthenticated_token(factory: MaybeTokenFactory) -> Any:
    """Возвращает токен по настройке UNAUTHENTICATED_TOKEN."""
    if callable(factory):
        return factory()
    return None
