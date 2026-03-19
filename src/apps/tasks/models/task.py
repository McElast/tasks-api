"""Модель задачи."""

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from ..enums import TaskStatus
from ..validation import normalize_text

if TYPE_CHECKING:
    from .comment import Comment


class Task(models.Model):
    """Модель пользовательской задачи."""

    author_id: int
    assignee_id: int | None
    comments: models.Manager[Comment]

    title = models.CharField('Заголовок', max_length=200)
    description = models.TextField('Описание', blank=True)
    status = models.CharField('Статус', max_length=20, choices=TaskStatus, default=TaskStatus.NEW)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Автор',
        related_name='authored_tasks',
        on_delete=models.CASCADE,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Исполнитель',
        related_name='assigned_tasks',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    is_completed = models.BooleanField('Завершена', default=False)
    completed_at = models.DateTimeField('Завершена в', null=True, blank=True)
    created_at = models.DateTimeField('Создана в', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена в', auto_now=True)

    class Meta:
        """Мета-настройки модели задачи."""

        ordering = ['-updated_at', '-created_at']
        indexes = [
            models.Index(fields=['author'], name='task_author_idx'),
            models.Index(fields=['assignee'], name='task_assignee_idx'),
            models.Index(fields=['status'], name='task_status_idx'),
            models.Index(fields=['is_completed'], name='task_completed_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(status=TaskStatus.DONE) & Q(is_completed=True))
                    | (~Q(status=TaskStatus.DONE) & Q(is_completed=False))
                ),
                name='task_completion_state_consistent',
            ),
        ]
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'

    def __str__(self) -> str:
        """Возвращает текстовое представление задачи."""
        return self.title

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Сохраняет задачу после полной валидации модели."""
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """Нормализует поля завершённости и валидирует заголовок."""
        super().clean()
        self.title = normalize_text(self.title)
        if not self.title:
            message = 'Заголовок задачи не может быть пустым.'
            raise ValidationError({'title': message})
        self._sync_completion_fields()

    def _sync_completion_fields(self) -> None:
        """Синхронизирует статус, флаг завершения и дату завершения."""
        if self.status == TaskStatus.DONE:
            self.is_completed = True
            self.completed_at = self.completed_at or timezone.now()
            return
        if self.is_completed:
            self.status = TaskStatus.DONE
            self.completed_at = self.completed_at or timezone.now()
            return
        self.completed_at = None

    def mark_completed(self) -> None:
        """Переводит задачу в завершённое состояние."""
        self.status = TaskStatus.DONE
        self.is_completed = True
        self.completed_at = timezone.now()

    def reopen(self, *, status: TaskStatus = TaskStatus.IN_PROGRESS) -> None:
        """Возвращает задачу в активное состояние."""
        if status == TaskStatus.DONE:
            status = TaskStatus.IN_PROGRESS
        self.status = status
        self.is_completed = False
        self.completed_at = None
