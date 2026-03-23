"""Вспомогательные функции и миксины для HTML-представлений задач."""

from collections.abc import Callable
from typing import Any

from asgiref.sync import sync_to_async
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse

from .forms import CommentForm, TaskForm
from .models import Task
from .selectors import filter_tasks_for_user
from .services import TaskUpdateData


def build_task_form(*, current_user: User, data: Any = None, instance: Task | None = None) -> TaskForm:
    """Создаёт форму задачи в синхронном контексте для безопасного вызова из async view."""
    return TaskForm(data=data, instance=instance, current_user=current_user)


def build_comment_form(*, data: Any = None) -> CommentForm:
    """Создаёт форму комментария в синхронном контексте."""
    return CommentForm(data=data)


def get_request_user(request: HttpRequest) -> User:
    """Возвращает типизированного пользователя запроса."""
    user = request.user
    if not isinstance(user, User):
        raise TypeError('Authenticated HTML request must contain django.contrib.auth User.')
    return user


async def get_async_request_user(request: HttpRequest) -> User:
    """Возвращает типизированного пользователя из async request.auser()."""
    user = await request.auser()
    if not isinstance(user, User):
        raise TypeError('Authenticated HTML request must contain django.contrib.auth User.')
    return user


async def run_sync[T](func: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Выполняет sync-функцию из async HTML view."""
    return await sync_to_async(func)(*args, **kwargs)


def task_form_context(*, form: TaskForm, page_title: str, submit_label: str) -> dict[str, Any]:
    """Собирает стандартный контекст страницы формы задачи."""
    return {
        'form': form,
        'page_title': page_title,
        'submit_label': submit_label,
    }


def get_user_task_or_404(*, user: User, task_id: int) -> Task:
    """Возвращает задачу пользователя или поднимает 404."""
    queryset = filter_tasks_for_user(user=user, filter_name='all')
    return get_object_or_404(queryset, pk=task_id)


def task_form_payload(form: TaskForm) -> TaskUpdateData:
    """Собирает payload обновления задачи из валидной формы."""
    return TaskUpdateData(
        title=form.cleaned_data['title'],
        description=form.cleaned_data['description'],
        status=form.cleaned_data['status'],
        assignee=form.cleaned_data['assignee'],
    )


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
