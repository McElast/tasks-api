"""Сервисный слой для доменной логики задач."""

from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .enums import TaskStatus
from .models import Comment, Task
from .validation import normalize_text

type TaskActor = User | AnonymousUser


@dataclass(slots=True)
class TaskUpdateData:
    """Данные для обновления задачи."""

    title: str
    description: str
    status: TaskStatus
    assignee: User | None


def can_view_task(*, actor: TaskActor, task: Task) -> bool:
    """Проверяет, может ли пользователь видеть задачу."""
    return actor.is_authenticated and (task.author_id == actor.pk or task.assignee_id == actor.pk)


def can_edit_task(*, actor: TaskActor, task: Task) -> bool:
    """Проверяет, может ли пользователь редактировать задачу."""
    return can_view_task(actor=actor, task=task)


def can_delete_task(*, actor: TaskActor, task: Task) -> bool:
    """Проверяет, может ли пользователь удалить задачу."""
    return actor.is_authenticated and task.author_id == actor.pk


def assert_can_view_task(*, actor: TaskActor, task: Task) -> None:
    """Выбрасывает исключение, если пользователь не может видеть задачу."""
    if not can_view_task(actor=actor, task=task):
        raise PermissionDenied('У вас нет доступа к этой задаче.')


def assert_can_edit_task(*, actor: TaskActor, task: Task) -> None:
    """Выбрасывает исключение, если пользователь не может редактировать задачу."""
    if not can_edit_task(actor=actor, task=task):
        raise PermissionDenied('У вас нет прав на изменение этой задачи.')


def assert_can_delete_task(*, actor: TaskActor, task: Task) -> None:
    """Выбрасывает исключение, если пользователь не может удалить задачу."""
    if not can_delete_task(actor=actor, task=task):
        raise PermissionDenied('Удалять задачу может только её автор.')


@transaction.atomic
def create_task(
    *,
    actor: User,
    title: str,
    description: str,
    assignee: User | None,
    status: TaskStatus = TaskStatus.NEW,
) -> Task:
    """Создаёт задачу от имени пользователя."""
    validate_task_payload(title=title, description=description)
    task = Task(
        author=actor,
        title=title,
        description=description,
        assignee=assignee,
        status=status,
        is_completed=status == TaskStatus.DONE,
    )
    task.save()
    return task


@transaction.atomic
def update_task(*, actor: User, task: Task, data: TaskUpdateData) -> Task:
    """Обновляет задачу с учётом правил доступа и назначения исполнителя."""
    assert_can_edit_task(actor=actor, task=task)
    validate_task_payload(title=data.title, description=data.description)
    if actor.pk != task.author_id and data.assignee != task.assignee:
        raise PermissionDenied('Только автор задачи может менять исполнителя.')
    task.title = data.title
    task.description = data.description
    task.status = data.status
    task.assignee = data.assignee
    task.is_completed = data.status == TaskStatus.DONE
    task.save()
    return task


@transaction.atomic
def delete_task(*, actor: User, task: Task) -> None:
    """Удаляет задачу, если действие выполняет её автор."""
    assert_can_delete_task(actor=actor, task=task)
    task.delete()


@transaction.atomic
def complete_task(*, actor: User, task: Task) -> Task:
    """Помечает задачу завершённой."""
    assert_can_edit_task(actor=actor, task=task)
    task.mark_completed()
    task.save()
    return task


@transaction.atomic
def reopen_task(*, actor: User, task: Task) -> Task:
    """Повторно открывает задачу для работы."""
    assert_can_edit_task(actor=actor, task=task)
    fallback_status = TaskStatus.IN_PROGRESS if task.assignee_id else TaskStatus.NEW
    task.reopen(status=fallback_status)
    task.save()
    return task


@transaction.atomic
def create_comment(*, actor: User, task: Task, text: str) -> Comment:
    """Создаёт комментарий к задаче для пользователя с доступом."""
    assert_can_view_task(actor=actor, task=task)
    comment = Comment(task=task, author=actor, text=text)
    comment.save()
    return comment


def validate_task_payload(*, title: str, description: str) -> None:
    """Выполняет прикладную валидацию данных задачи."""
    if not normalize_text(title):
        raise ValidationError({'title': 'Заголовок задачи не может быть пустым.'})
    if description is None:
        raise ValidationError({'description': 'Описание задачи должно быть строкой.'})
