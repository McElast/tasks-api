"""Совместимая async-версия APIView без deprecated asyncio helpers."""

import asyncio
from collections.abc import Awaitable
from typing import Any

from asgiref.sync import async_to_sync, sync_to_async
from django.http import HttpRequest, HttpResponseBase
from rest_framework import exceptions
from rest_framework.request import Request, wrap_attributeerrors
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView as DRFAPIView

from .async_support import (
    AsyncAuthenticate,
    AsyncHandler,
    AsyncObjectPermissionCheck,
    AsyncPermissionCheck,
    AsyncThrottleCheck,
    RequestUser,
    SyncAuthenticate,
    SyncHandler,
    SyncObjectPermissionCheck,
    SyncPermissionCheck,
    SyncThrottleCheck,
    has_async_object_permission,
    has_async_permission,
    has_async_throttle,
    is_async_authenticate,
    is_async_handler,
    resolve_unauthenticated_token,
    resolve_unauthenticated_user,
)


class AsyncRequest(Request):
    """Совместимая версия DRF Request с поддержкой async authenticator."""

    _authenticator: Any | None
    _auth: Any
    _user: RequestUser

    @property
    def user(self) -> RequestUser:
        """Возвращает аутентифицированного пользователя запроса."""
        if not hasattr(self, '_user'):
            with wrap_attributeerrors():
                self._authenticate()
        return self._user

    @user.setter
    def user(self, value: RequestUser) -> None:
        """Синхронизирует пользователя с базовым Django HttpRequest."""
        self._user = value
        self._request.user = value

    def _set_not_authenticated(self) -> None:
        """Устанавливает состояние неаутентифицированного запроса."""
        self._authenticator = None
        self.user = resolve_unauthenticated_user(api_settings.UNAUTHENTICATED_USER)
        self.auth = resolve_unauthenticated_token(api_settings.UNAUTHENTICATED_TOKEN)

    def _authenticate(self) -> None:
        """Аутентифицирует запрос через sync или async authenticator."""
        for authenticator in self.authenticators or ():
            try:
                authenticate: SyncAuthenticate | AsyncAuthenticate = authenticator.authenticate
                if is_async_authenticate(authenticate):
                    user_auth_tuple = async_to_sync(authenticate)(self)
                else:
                    user_auth_tuple = authenticate(self)
            except exceptions.APIException:
                self._set_not_authenticated()
                raise

            if user_auth_tuple is None:
                continue

            self._authenticator = authenticator
            self.user, self.auth = user_auth_tuple
            return

        self._set_not_authenticated()


class AsyncAPIView(DRFAPIView):
    """Локальная async-совместимая версия View."""

    def _prepare_request(self, request: HttpRequest, *args: Any, **kwargs: Any) -> AsyncRequest:
        """Инициализирует DRF request и общее состояние view."""
        self.args = args
        self.kwargs = kwargs
        drf_request = self.initialize_request(request, *args, **kwargs)
        self.request = drf_request
        self.headers = self.default_response_headers
        return drf_request

    def _finalize_handled_response(
        self,
        request: Request,
        response: Response,
        *args: Any,
        **kwargs: Any,
    ) -> Response:
        """Финализирует обработанный ответ и сохраняет его в self.response."""
        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    def _get_handler(self, request: Request) -> SyncHandler | AsyncHandler:
        """Возвращает обработчик HTTP-метода."""
        method = (request.method or '').lower()
        if method in self.http_method_names:
            return getattr(self, method, self.http_method_not_allowed)
        return self.http_method_not_allowed

    def _split_permissions(self) -> tuple[list[SyncPermissionCheck], list[AsyncPermissionCheck]]:
        """Разделяет permissions на sync и async группы."""
        permissions: list[SyncPermissionCheck | AsyncPermissionCheck] = list(self.get_permissions())
        sync_permissions: list[SyncPermissionCheck] = []
        async_permissions: list[AsyncPermissionCheck] = []

        for permission in permissions:
            if has_async_permission(permission):
                async_permissions.append(permission)
            else:
                sync_permissions.append(permission)

        return sync_permissions, async_permissions

    def _split_object_permissions(
        self,
    ) -> tuple[list[SyncObjectPermissionCheck], list[AsyncObjectPermissionCheck]]:
        """Разделяет object permissions на sync и async группы."""
        permissions: list[SyncObjectPermissionCheck | AsyncObjectPermissionCheck] = list(self.get_permissions())
        sync_permissions: list[SyncObjectPermissionCheck] = []
        async_permissions: list[AsyncObjectPermissionCheck] = []

        for permission in permissions:
            if has_async_object_permission(permission):
                async_permissions.append(permission)
            else:
                sync_permissions.append(permission)

        return sync_permissions, async_permissions

    def _split_throttles(self) -> tuple[list[SyncThrottleCheck], list[AsyncThrottleCheck]]:
        """Разделяет throttles на sync и async группы."""
        throttles: list[SyncThrottleCheck | AsyncThrottleCheck] = list(self.get_throttles())
        sync_throttles: list[SyncThrottleCheck] = []
        async_throttles: list[AsyncThrottleCheck] = []

        for throttle in throttles:
            if has_async_throttle(throttle):
                async_throttles.append(throttle)
            else:
                sync_throttles.append(throttle)

        return sync_throttles, async_throttles

    def sync_dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        """Синхронно обрабатывает запрос."""
        drf_request = self._prepare_request(request, *args, **kwargs)

        try:
            self.initial(drf_request, *args, **kwargs)
            handler = self._get_handler(drf_request)
            if is_async_handler(handler):
                raise RuntimeError('sync_dispatch cannot execute async handlers.')
            response = handler(drf_request, *args, **kwargs)
        except Exception as exc:
            response = self.handle_exception(exc)

        return self._finalize_handled_response(drf_request, response, *args, **kwargs)

    @staticmethod
    async def _call_sync_handler(handler: SyncHandler, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Выполняет sync handler из async-контекста."""
        return await sync_to_async(handler)(request, *args, **kwargs)

    async def async_dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        """Асинхронно обрабатывает запрос."""
        drf_request = self._prepare_request(request, *args, **kwargs)

        try:
            await sync_to_async(self.initial)(drf_request, *args, **kwargs)
            handler = self._get_handler(drf_request)
            if is_async_handler(handler):
                response = await handler(drf_request, *args, **kwargs)
            else:
                response = await self._call_sync_handler(handler, drf_request, *args, **kwargs)
        except Exception as exc:
            response = self.handle_exception(exc)

        return self._finalize_handled_response(drf_request, response, *args, **kwargs)

    def dispatch(  # type: ignore[override]
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        """Выбирает sync или async dispatch в зависимости от view handlers."""
        if self.view_is_async:
            return self.async_dispatch(request, *args, **kwargs)
        return self.sync_dispatch(request, *args, **kwargs)

    def initialize_request(self, request: HttpRequest, *args: Any, **kwargs: Any) -> AsyncRequest:
        """Создаёт совместимый AsyncRequest без deprecated asyncio helpers."""
        parser_context = self.get_parser_context(request)
        return AsyncRequest(
            request,
            parsers=self.get_parsers(),
            authenticators=self.get_authenticators(),
            negotiator=self.get_content_negotiator(),
            parser_context=parser_context,
        )

    def _deny_by_permission(self, request: Request, permission: object) -> None:
        """Выбрасывает стандартный DRF deny с метаданными permission."""
        self.permission_denied(
            request,
            message=getattr(permission, 'detail', None),
            code=getattr(permission, 'code', None),
        )

    def _handle_permission_result(self, request: Request, permission: object, result: bool | BaseException) -> None:
        """Преобразует результат permission-проверки в исключение доступа при необходимости."""
        if isinstance(result, BaseException):
            raise result
        if not result:
            self._deny_by_permission(request, permission)

    def check_permissions(self, request: Request) -> None:
        """Проверяет права доступа для sync и async permission classes."""
        sync_permissions, async_permissions = self._split_permissions()

        if async_permissions:
            async_to_sync(self.check_async_permissions)(request, async_permissions)
        if sync_permissions:
            self.check_sync_permissions(request, sync_permissions)

    async def check_async_permissions(self, request: Request, permissions: list[AsyncPermissionCheck]) -> None:
        """Проверяет async permissions."""
        results = await asyncio.gather(
            *(permission.has_permission(request, self) for permission in permissions),
            return_exceptions=True,
        )
        for permission, result in zip(permissions, results, strict=False):
            self._handle_permission_result(request, permission, result)

    def check_sync_permissions(self, request: Request, permissions: list[SyncPermissionCheck]) -> None:
        """Проверяет sync permissions."""
        for permission in permissions:
            self._handle_permission_result(request, permission, permission.has_permission(request, self))

    def check_object_permissions(self, request: Request, obj: Any) -> None:
        """Проверяет объектные права доступа для sync и async permission classes."""
        sync_permissions, async_permissions = self._split_object_permissions()

        if async_permissions:
            async_to_sync(self.check_async_object_permissions)(request, async_permissions, obj)
        if sync_permissions:
            self.check_sync_object_permissions(request, sync_permissions, obj)

    async def check_async_object_permissions(
        self,
        request: Request,
        permissions: list[AsyncObjectPermissionCheck],
        obj: Any,
    ) -> None:
        """Проверяет async object permissions."""
        results = await asyncio.gather(
            *(permission.has_object_permission(request, self, obj) for permission in permissions),
            return_exceptions=True,
        )
        for permission, result in zip(permissions, results, strict=False):
            self._handle_permission_result(request, permission, result)

    def check_sync_object_permissions(
        self,
        request: Request,
        permissions: list[SyncObjectPermissionCheck],
        obj: Any,
    ) -> None:
        """Проверяет sync object permissions."""
        for permission in permissions:
            result = permission.has_object_permission(request, self, obj)
            self._handle_permission_result(request, permission, result)

    def check_throttles(self, request: Request) -> None:
        """Проверяет throttles для sync и async throttle classes."""
        sync_throttles, async_throttles = self._split_throttles()
        throttle_durations = self.check_sync_throttles(request, sync_throttles)
        throttle_durations.extend(async_to_sync(self.check_async_throttles)(request, async_throttles))

        if throttle_durations:
            durations = [duration for duration in throttle_durations if duration is not None]
            self.throttled(request, max(durations, default=0.0))

    async def check_async_throttles(
        self,
        request: Request,
        throttles: list[AsyncThrottleCheck],
    ) -> list[float | None]:
        """Проверяет async throttles."""
        throttle_durations: list[float | None] = []
        for throttle in throttles:
            if not await throttle.allow_request(request, self):
                throttle_durations.append(throttle.wait())
        return throttle_durations

    def check_sync_throttles(self, request: Request, throttles: list[SyncThrottleCheck]) -> list[float | None]:
        """Проверяет sync throttles."""
        throttle_durations: list[float | None] = []
        for throttle in throttles:
            if not throttle.allow_request(request, self):
                throttle_durations.append(throttle.wait())
        return throttle_durations
