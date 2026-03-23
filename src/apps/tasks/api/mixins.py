"""Миксины для REST API-представлений задач."""

from typing import Protocol, runtime_checkable

from django.http import Http404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from ..async_utils import run_sync
from ..models import Task
from .serializers import TaskSerializer
from .view_helpers import get_task_or_404


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
            task = await run_sync(get_task_or_404, task_id)
        except Http404 as error:
            raise Http404('Задача не найдена.') from error
        if not isinstance(self, SupportsObjectPermissions):
            raise TypeError('View must implement check_object_permissions().')
        self.check_object_permissions(request, task)
        return task

    @staticmethod
    async def task_response(request: Request, task: Task, *, status_code: int = status.HTTP_200_OK) -> Response:
        """Сериализует задачу и возвращает стандартный Response."""
        payload = await run_sync(lambda: TaskSerializer(task, context={'request': request}).data)
        return Response(payload, status=status_code)
