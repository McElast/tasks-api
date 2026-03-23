"""Вспомогательные функции и константы для REST API-представлений задач."""

from collections.abc import Callable, Mapping
from typing import Any

from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse
from rest_framework import status
from rest_framework.request import Request

from ..models import Task
from .serializers import CommentSerializer, TaskSerializer, UserSerializer

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


def task_base_queryset() -> QuerySet[Task]:
    """Возвращает базовый queryset задач для детальных операций API."""
    return Task.objects.select_related('author', 'assignee').prefetch_related('comments__author')


def get_task_or_404(task_id: int) -> Task:
    """Возвращает задачу по идентификатору или поднимает 404."""
    return get_object_or_404(task_base_queryset(), pk=task_id)


def as_object_payload(data: Any) -> dict[str, Any]:
    """Преобразует данные сериализатора в словарь ответа API."""
    if not isinstance(data, Mapping):
        raise TypeError('Serializer data must be a mapping.')
    return {str(key): value for key, value in data.items()}


def as_list_payload(data: Any) -> list[dict[str, Any]]:
    """Преобразует список данных сериализатора в список словарей ответа API."""
    if not isinstance(data, list):
        raise TypeError('Serializer data must be a list.')
    payload: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, Mapping):
            raise TypeError('Serializer list item must be a mapping.')
        payload.append({str(key): value for key, value in item.items()})
    return payload


def serialize_user(user: User) -> dict[str, Any]:
    """Сериализует пользователя для ответа API."""
    return as_object_payload(UserSerializer(user).data)


def serialize_task(task: Task, *, request: Request) -> dict[str, Any]:
    """Сериализует одну задачу для ответа API."""
    return as_object_payload(TaskSerializer(task, context={'request': request}).data)


def serialize_tasks(tasks: list[Task], *, request: Request) -> list[dict[str, Any]]:
    """Сериализует список задач для ответа API."""
    return as_list_payload(TaskSerializer(tasks, many=True, context={'request': request}).data)


def serialize_comments(task: Task) -> list[dict[str, Any]]:
    """Сериализует комментарии задачи для ответа API."""
    return as_list_payload(CommentSerializer(task.comments.all(), many=True).data)


def serialize_comment(comment: Any) -> dict[str, Any]:
    """Сериализует один комментарий для ответа API."""
    return as_object_payload(CommentSerializer(comment).data)


def build_task_serializer(*, request: Request, instance: Task | None = None, data: Any = None) -> TaskSerializer:
    """Создаёт сериализатор задачи для синхронной работы из async view."""
    return TaskSerializer(instance=instance, data=data, partial=instance is not None, context={'request': request})


def build_comment_serializer(*, data: Any) -> CommentSerializer:
    """Создаёт сериализатор комментария для синхронной работы из async view."""
    return CommentSerializer(data=data)


def get_request_user(request: Request) -> User:
    """Возвращает типизированного пользователя запроса."""
    user = request.user
    if not isinstance(user, User):
        raise TypeError('Authenticated API request must contain django.contrib.auth User.')
    return user


async def run_sync[T](func: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Выполняет sync-функцию из async view."""
    return await sync_to_async(func)(*args, **kwargs)
