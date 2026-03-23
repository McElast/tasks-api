"""Миксины для HTML-представлений задач."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse

from .models import Task
from .view_helpers import get_request_user, get_user_task_or_404, run_sync


class UserTaskAccessMixin(LoginRequiredMixin):
    """Общие async-утилиты для HTML views задач."""

    @staticmethod
    async def get_request_user(request: HttpRequest) -> User:
        """Возвращает типизированного пользователя запроса."""
        return get_request_user(request)

    async def get_user_task(self, request: HttpRequest, task_id: int) -> Task:
        """Возвращает задачу, доступную текущему пользователю."""
        return await run_sync(get_user_task_or_404, user=await self.get_request_user(request), task_id=task_id)

    async def get_deletable_task(self, request: HttpRequest, task_id: int) -> Task:
        """Возвращает задачу, которую текущий пользователь может удалить."""
        user = await self.get_request_user(request)
        task = await self.get_user_task(request, task_id)
        if task.author_id != user.pk:
            raise PermissionDenied('Удалять задачу может только её автор.')
        return task

    @staticmethod
    def redirect_to_task(task_id: int) -> HttpResponseRedirect:
        """Перенаправляет на карточку задачи."""
        return HttpResponseRedirect(reverse('task-detail', kwargs={'task_id': task_id}))
