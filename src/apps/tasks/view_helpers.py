"""Вспомогательные функции для HTML-представлений задач."""

from typing import Any

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from .async_utils import assert_user
from .forms import CommentForm, TaskForm
from .models import Task
from .selectors import filter_tasks_for_user


def build_task_form(*, current_user: User, data: Any = None, instance: Task | None = None) -> TaskForm:
    """Создаёт форму задачи в синхронном контексте для безопасного вызова из async view."""
    return TaskForm(data=data, instance=instance, current_user=current_user)


def build_comment_form(*, data: Any = None) -> CommentForm:
    """Создаёт форму комментария в синхронном контексте."""
    return CommentForm(data=data)


def get_request_user(request: HttpRequest) -> User:
    """Возвращает типизированного пользователя запроса."""
    return assert_user(request.user, context='Authenticated HTML request')


async def get_async_request_user(request: HttpRequest) -> User:
    """Возвращает типизированного пользователя из async request.auser()."""
    user = await request.auser()
    return assert_user(user, context='Authenticated HTML request')


def get_filter_from_request(request: HttpRequest) -> str | None:
    """Возвращает значение фильтра задач из запроса."""
    return request.GET.get('filter')


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
