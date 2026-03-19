"""Права доступа для REST API задач."""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from ..models import Task
from ..services import can_delete_task, can_edit_task, can_view_task


class TaskAccessPermission(BasePermission):
    """Проверяет доступ пользователя к задаче."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Разрешает работу только авторизованным пользователям."""
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: Task) -> bool:
        """Проверяет объектные права в зависимости от HTTP-метода."""
        if request.method in SAFE_METHODS:
            return can_view_task(actor=request.user, task=obj)
        if request.method == 'DELETE':
            return can_delete_task(actor=request.user, task=obj)
        return can_edit_task(actor=request.user, task=obj)
