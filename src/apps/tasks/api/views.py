"""Полностью асинхронные REST API-представления для задач и пользователей."""

from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable

from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from ..models import Task
from ..selectors import TaskFilter, filter_tasks_for_user
from ..services import complete_task, create_comment, reopen_task
from .async_api_view import AsyncAPIView
from .permissions import TaskAccessPermission
from .serializers import CommentSerializer, TaskSerializer, UserSerializer

APIView = AsyncAPIView

TASK_ACCESS_ERROR_RESPONSES = {
    status.HTTP_403_FORBIDDEN: OpenApiResponse(description='Нет доступа.'),
    status.HTTP_404_NOT_FOUND: OpenApiResponse(description='Задача не найдена.'),
}
TASK_DETAIL_RESPONSES = {
    status.HTTP_200_OK: TaskSerializer,
    **TASK_ACCESS_ERROR_RESPONSES,
}
TASK_DELETE_RESPONSES = {
    status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Задача удалена.'),
    **TASK_ACCESS_ERROR_RESPONSES,
}
COMMENT_LIST_RESPONSES = {
    status.HTTP_200_OK: CommentSerializer(many=True),
    **TASK_ACCESS_ERROR_RESPONSES,
}
COMMENT_CREATE_RESPONSES = {
    status.HTTP_201_CREATED: CommentSerializer,
    **TASK_ACCESS_ERROR_RESPONSES,
}


def _resolve_filter_name(raw_filter: str | None) -> TaskFilter:
    """Нормализует имя фильтра задач для REST API."""
    if raw_filter == 'mine':
        return 'mine'
    if raw_filter == 'assigned':
        return 'assigned'
    if raw_filter == 'completed':
        return 'completed'
    if raw_filter == 'active':
        return 'active'
    return 'all'


def _task_base_queryset() -> QuerySet[Task]:
    """Возвращает базовый queryset задач для детальных операций API."""
    return Task.objects.select_related('author', 'assignee').prefetch_related('comments__author')


def _get_task_or_404(task_id: int) -> Task:
    """Возвращает задачу по идентификатору или поднимает 404."""
    return get_object_or_404(_task_base_queryset(), pk=task_id)


def _as_object_payload(data: Any) -> dict[str, Any]:
    """Преобразует данные сериализатора в словарь ответа API."""
    if not isinstance(data, Mapping):
        raise TypeError('Serializer data must be a mapping.')
    return {str(key): value for key, value in data.items()}


def _as_list_payload(data: Any) -> list[dict[str, Any]]:
    """Преобразует список данных сериализатора в список словарей ответа API."""
    if not isinstance(data, list):
        raise TypeError('Serializer data must be a list.')
    payload: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, Mapping):
            raise TypeError('Serializer list item must be a mapping.')
        payload.append({str(key): value for key, value in item.items()})
    return payload


def _serialize_user(user: User) -> dict[str, Any]:
    """Сериализует пользователя для ответа API."""
    return _as_object_payload(UserSerializer(user).data)


def _serialize_task(task: Task, *, request: Request) -> dict[str, Any]:
    """Сериализует одну задачу для ответа API."""
    return _as_object_payload(TaskSerializer(task, context={'request': request}).data)


def _serialize_tasks(tasks: list[Task], *, request: Request) -> list[dict[str, Any]]:
    """Сериализует список задач для ответа API."""
    return _as_list_payload(TaskSerializer(tasks, many=True, context={'request': request}).data)


def _serialize_comments(task: Task) -> list[dict[str, Any]]:
    """Сериализует комментарии задачи для ответа API."""
    return _as_list_payload(CommentSerializer(task.comments.all(), many=True).data)


def _serialize_comment(comment: Any) -> dict[str, Any]:
    """Сериализует один комментарий для ответа API."""
    return _as_object_payload(CommentSerializer(comment).data)


def _build_task_serializer(*, request: Request, instance: Task | None = None, data: Any = None) -> TaskSerializer:
    """Создаёт сериализатор задачи для синхронной работы из async view."""
    return TaskSerializer(instance=instance, data=data, partial=instance is not None, context={'request': request})


def _build_comment_serializer(*, data: Any) -> CommentSerializer:
    """Создаёт сериализатор комментария для синхронной работы из async view."""
    return CommentSerializer(data=data)


def _get_request_user(request: Request) -> User:
    """Возвращает типизированного пользователя запроса."""
    user = request.user
    if not isinstance(user, User):
        raise TypeError('Authenticated API request must contain django.contrib.auth User.')
    return user


async def _run_sync[T](func: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Выполняет sync-функцию из async view."""
    return await sync_to_async(func)(*args, **kwargs)


@runtime_checkable
class SupportsObjectPermissions(Protocol):
    """Протокол для представлений с объектной проверкой прав."""

    def check_object_permissions(self, request: Request, obj: Task) -> None:
        """Проверяет объектные права доступа."""


class TaskObjectPermissionMixin:
    """Переиспользуемая асинхронная загрузка задачи с объектной проверкой прав."""

    async def get_task_with_permissions(self, *, request: Request, task_id: int) -> Task:
        """Возвращает задачу и проверяет объектные права доступа."""
        try:
            task = await _run_sync(_get_task_or_404, task_id)
        except Http404 as error:
            raise Http404('Задача не найдена.') from error
        if not isinstance(self, SupportsObjectPermissions):
            raise TypeError('View must implement check_object_permissions().')
        self.check_object_permissions(request, task)
        return task

    @staticmethod
    async def task_response(request: Request, task: Task, *, status_code: int = status.HTTP_200_OK) -> Response:
        """Сериализует задачу и возвращает стандартный Response."""
        return Response(await _run_sync(_serialize_task, task, request=request), status=status_code)


class UserMeAPIView(APIView):
    """Возвращает данные текущего пользователя."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['users'],
        summary='Получить профиль текущего пользователя',
        responses={status.HTTP_200_OK: UserSerializer},
    )
    async def get(self, request: Request) -> Response:
        """Сериализует текущего пользователя и возвращает ответ API."""
        return Response(await _run_sync(_serialize_user, _get_request_user(request)))


class TaskListCreateAPIView(APIView):
    """Асинхронно обрабатывает список задач и создание новой задачи."""

    permission_classes = [TaskAccessPermission]

    @extend_schema(
        tags=['tasks'],
        summary='Получить список доступных задач',
        responses={status.HTTP_200_OK: TaskSerializer(many=True)},
    )
    async def get(self, request: Request) -> Response:
        """Возвращает список задач, доступных текущему пользователю."""
        filter_name = _resolve_filter_name(request.query_params.get('filter'))
        tasks = await _run_sync(lambda: list(filter_tasks_for_user(user=request.user, filter_name=filter_name)))
        return Response(await _run_sync(_serialize_tasks, tasks, request=request))

    @extend_schema(
        tags=['tasks'],
        summary='Создать задачу',
        request=TaskSerializer,
        responses={status.HTTP_201_CREATED: TaskSerializer},
    )
    async def post(self, request: Request) -> Response:
        """Создаёт задачу через сериализатор и сервисный слой."""
        serializer = await _run_sync(_build_task_serializer, request=request, data=request.data)
        await _run_sync(serializer.is_valid, raise_exception=True)
        task = await _run_sync(serializer.save)
        return Response(await _run_sync(_serialize_task, task, request=request), status=status.HTTP_201_CREATED)


class TaskDetailAPIView(TaskObjectPermissionMixin, APIView):
    """Асинхронно обрабатывает чтение, обновление и удаление задачи."""

    permission_classes = [TaskAccessPermission]

    @extend_schema(
        tags=['tasks'],
        summary='Получить задачу по идентификатору',
        responses=TASK_DETAIL_RESPONSES,
    )
    async def get(self, request: Request, task_id: int) -> Response:
        """Возвращает детальную информацию по задаче."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        return await self.task_response(request, task)

    @extend_schema(
        tags=['tasks'],
        summary='Частично обновить задачу',
        request=TaskSerializer,
        responses=TASK_DETAIL_RESPONSES,
    )
    async def patch(self, request: Request, task_id: int) -> Response:
        """Обновляет задачу через сериализатор и сервисный слой."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        serializer = await _run_sync(_build_task_serializer, request=request, instance=task, data=request.data)
        await _run_sync(serializer.is_valid, raise_exception=True)
        updated_task = await _run_sync(serializer.save)
        return await self.task_response(request, updated_task)

    @extend_schema(
        tags=['tasks'],
        summary='Удалить задачу',
        responses=TASK_DELETE_RESPONSES,
    )
    async def delete(self, request: Request, task_id: int) -> Response:
        """Удаляет задачу, если это делает её автор."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        await _run_sync(task.delete)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskCompleteAPIView(TaskObjectPermissionMixin, APIView):
    """Асинхронно переводит задачу в завершённое состояние."""

    permission_classes = [TaskAccessPermission]
    serializer_class = TaskSerializer

    @extend_schema(
        tags=['tasks'],
        summary='Завершить задачу',
        request=None,
        responses=TASK_DETAIL_RESPONSES,
    )
    async def post(self, request: Request, task_id: int) -> Response:
        """Переводит задачу в статус done."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        updated_task = await _run_sync(complete_task, actor=_get_request_user(request), task=task)
        return await self.task_response(request, updated_task)


class TaskReopenAPIView(TaskObjectPermissionMixin, APIView):
    """Асинхронно возвращает завершённую задачу в активное состояние."""

    permission_classes = [TaskAccessPermission]
    serializer_class = TaskSerializer

    @extend_schema(
        tags=['tasks'],
        summary='Повторно открыть задачу',
        request=None,
        responses=TASK_DETAIL_RESPONSES,
    )
    async def post(self, request: Request, task_id: int) -> Response:
        """Снимает признак завершённости с задачи."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        updated_task = await _run_sync(reopen_task, actor=_get_request_user(request), task=task)
        return await self.task_response(request, updated_task)


class TaskCommentListCreateAPIView(TaskObjectPermissionMixin, APIView):
    """Асинхронно читает и создаёт комментарии для задачи."""

    permission_classes = [TaskAccessPermission]

    @extend_schema(
        tags=['comments'],
        summary='Получить комментарии задачи',
        responses=COMMENT_LIST_RESPONSES,
    )
    async def get(self, request: Request, task_id: int) -> Response:
        """Возвращает список комментариев для доступной задачи."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        return Response(await _run_sync(_serialize_comments, task))

    @extend_schema(
        tags=['comments'],
        summary='Добавить комментарий к задаче',
        request=CommentSerializer,
        responses=COMMENT_CREATE_RESPONSES,
    )
    async def post(self, request: Request, task_id: int) -> Response:
        """Создаёт комментарий через сервисный слой."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        serializer = await _run_sync(_build_comment_serializer, data=request.data)
        await _run_sync(serializer.is_valid, raise_exception=True)
        comment = await _run_sync(
            create_comment,
            actor=_get_request_user(request),
            task=task,
            text=str(serializer.validated_data['text']),
        )
        return Response(await _run_sync(_serialize_comment, comment), status=status.HTTP_201_CREATED)
