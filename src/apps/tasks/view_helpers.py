"""Вспомогательные функции для HTML-представлений задач."""

from collections.abc import Callable
from typing import Any

from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.shortcuts import get_object_or_404

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
