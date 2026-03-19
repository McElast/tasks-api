"""Тесты моделей задач и комментариев."""

import pytest

from ..enums import TaskStatus
from ..models import Comment, Task

pytestmark = [pytest.mark.django_db, pytest.mark.module]


def test_task_is_created_with_expected_fields(user: object) -> None:
    """Проверяет корректное создание модели задачи."""
    task = Task.objects.create(
        title='Собрать релиз',
        description='Проверить последние правки.',
        author=user,
        status=TaskStatus.NEW,
    )

    assert task.title == 'Собрать релиз'
    assert task.is_completed is False
    assert task.completed_at is None


def test_task_syncs_completion_flag_with_done_status(user: object) -> None:
    """Проверяет синхронизацию флага завершения со статусом done."""
    task = Task.objects.create(
        title='Закрыть инцидент',
        description='Нужно зафиксировать решение.',
        author=user,
        status=TaskStatus.DONE,
    )

    assert task.is_completed is True
    assert task.completed_at is not None


def test_task_clears_completed_at_after_reopen(task: Task) -> None:
    """Проверяет очистку даты завершения после повторного открытия."""
    task.mark_completed()
    task.save()

    task.reopen(status=TaskStatus.IN_PROGRESS)
    task.save()

    assert task.is_completed is False
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.completed_at is None


def test_comment_is_created_for_task(task: Task, user: object) -> None:
    """Проверяет создание комментария к задаче."""
    comment = Comment.objects.create(task=task, author=user, text='Комментарий по задаче')

    assert comment.text == 'Комментарий по задаче'
    assert comment.task == task
