"""Тесты сервисного слоя приложения задач."""

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from ..enums import TaskStatus
from ..models import Task
from ..services import (
    TaskUpdateData,
    complete_task,
    create_comment,
    create_task,
    delete_task,
    reopen_task,
    update_task,
)

pytestmark = [pytest.mark.django_db, pytest.mark.module]


def test_create_task_creates_expected_object(user: User, second_user: User) -> None:
    """Проверяет создание задачи через сервисный слой."""
    task = create_task(
        actor=user,
        title='Подготовить план',
        description='Нужно согласовать этапы.',
        assignee=second_user,
        status=TaskStatus.NEW,
    )

    assert task.author == user
    assert task.assignee == second_user
    assert task.status == TaskStatus.NEW


def test_update_task_allows_assignee_to_change_content_but_not_assignee(
    task: Task,
    second_user: User,
    user: User,
) -> None:
    """Проверяет правила обновления задачи для исполнителя."""
    payload = TaskUpdateData(
        title='Обновлённый заголовок',
        description='Новое описание',
        status=TaskStatus.IN_PROGRESS,
        assignee=user,
    )

    with pytest.raises(PermissionDenied):
        update_task(actor=second_user, task=task, data=payload)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_complete_task_marks_task_as_done(task: Task, user: User) -> None:
    """Проверяет асинхронный вызов завершения задачи через сервис."""
    updated_task = await sync_to_async(complete_task)(actor=user, task=task)

    assert updated_task.status == TaskStatus.DONE
    assert updated_task.is_completed is True
    assert updated_task.completed_at is not None


def test_reopen_task_returns_task_to_active_state(task: Task, second_user: User) -> None:
    """Проверяет повторное открытие завершённой задачи."""
    task.mark_completed()
    task.save()

    reopened_task = reopen_task(actor=second_user, task=task)

    assert reopened_task.is_completed is False
    assert reopened_task.status == TaskStatus.IN_PROGRESS


def test_delete_task_is_available_only_for_author(task: Task, second_user: User, user: User) -> None:
    """Проверяет ограничения на удаление задачи."""
    with pytest.raises(PermissionDenied):
        delete_task(actor=second_user, task=task)

    task_id = task.pk
    delete_task(actor=user, task=task)

    assert not task.__class__.objects.filter(pk=task_id).exists()


def test_create_comment_requires_task_access(task: Task, outsider: User, user: User) -> None:
    """Проверяет ограничение доступа при создании комментария."""
    with pytest.raises(PermissionDenied):
        create_comment(actor=outsider, task=task, text='Чужой комментарий')

    comment = create_comment(actor=user, task=task, text='Рабочий комментарий')

    assert comment.text == 'Рабочий комментарий'
