"""Селекторы для чтения задач и комментариев."""

from typing import Literal

from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Case, IntegerField, Prefetch, Q, QuerySet, Value, When

from .enums import TaskStatus
from .models import Comment, Task

type TaskActor = User | AnonymousUser
type TaskFilter = Literal['all', 'mine', 'assigned', 'completed', 'active']


def task_base_queryset(*, with_comments: bool = True) -> QuerySet[Task]:
    """Возвращает базовый queryset задач с основными связями."""
    queryset = Task.objects.select_related('author', 'assignee')
    if with_comments:
        queryset = queryset.prefetch_related(
            Prefetch('comments', queryset=Comment.objects.select_related('author').order_by('created_at')),
        )
    return queryset


def resolve_task_filter(raw_filter: str | None) -> TaskFilter:
    """Нормализует имя фильтра задач."""
    match raw_filter:
        case 'mine' | 'assigned' | 'completed' | 'active':
            return raw_filter
        case _:
            return 'all'


def visible_tasks_for_user(user: TaskActor) -> QuerySet[Task]:
    """Возвращает queryset задач, доступных пользователю."""
    if not user.is_authenticated:
        return Task.objects.none()
    return (
        task_base_queryset(with_comments=True)
        .filter(Q(author=user) | Q(assignee=user))
        .alias(
            status_order=Case(
                When(status=TaskStatus.NEW, then=Value(0)),
                When(status=TaskStatus.IN_PROGRESS, then=Value(1)),
                When(status=TaskStatus.DONE, then=Value(2)),
                default=Value(99),
                output_field=IntegerField(),
            )
        )
        .order_by('status_order', '-updated_at', '-created_at')
        .distinct()
    )


def filter_tasks_for_user(*, user: TaskActor, filter_name: TaskFilter) -> QuerySet[Task]:
    """Фильтрует доступные задачи пользователя по выбранному режиму."""
    if not user.is_authenticated:
        return Task.objects.none()
    queryset = visible_tasks_for_user(user)
    if filter_name == 'mine':
        return queryset.filter(author=user)
    if filter_name == 'assigned':
        return queryset.filter(assignee=user)
    if filter_name == 'completed':
        return queryset.filter(is_completed=True)
    if filter_name == 'active':
        return queryset.filter(is_completed=False)
    return queryset
