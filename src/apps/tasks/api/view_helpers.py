"""Вспомогательные функции и константы для REST API-представлений задач."""

from typing import Any

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse
from rest_framework import status
from rest_framework.request import Request

from ..async_utils import assert_user
from ..models import Task
from ..selectors import task_base_queryset
from .serializers import CommentSerializer, TaskSerializer

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


def get_task_or_404(task_id: int) -> Task:
    """Возвращает задачу по идентификатору или поднимает 404."""
    return get_object_or_404(task_base_queryset(with_comments=True), pk=task_id)


def build_task_serializer(*, request: Request, instance: Task | None = None, data: Any = None) -> TaskSerializer:
    """Создаёт сериализатор задачи для синхронной работы из async view."""
    return TaskSerializer(instance=instance, data=data, partial=instance is not None, context={'request': request})


def build_comment_serializer(*, data: Any) -> CommentSerializer:
    """Создаёт сериализатор комментария для синхронной работы из async view."""
    return CommentSerializer(data=data)


def get_request_user(request: Request) -> User:
    """Возвращает типизированного пользователя запроса."""
    return assert_user(request.user, context='Authenticated API request')


def get_filter_from_request(request: Request) -> str | None:
    """Возвращает значение фильтра задач из запроса API."""
    return request.query_params.get('filter')
