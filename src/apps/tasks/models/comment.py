"""Модель комментария."""

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from ..validation import normalize_text


class Comment(models.Model):
    """Модель комментария к задаче."""

    task = models.ForeignKey('tasks.Task', verbose_name='Задача', related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Автор',
        related_name='task_comments',
        on_delete=models.CASCADE,
    )
    text = models.TextField('Текст')
    created_at = models.DateTimeField('Создан в', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён в', auto_now=True)

    class Meta:
        """Мета-настройки модели комментария."""

        ordering = ['created_at']
        indexes = [models.Index(fields=['task', 'created_at'], name='comment_task_created_idx')]
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self) -> str:
        """Возвращает текстовое представление комментария."""
        return f'Комментарий #{self.pk}'

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Сохраняет комментарий после полной валидации."""
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """Проверяет, что текст комментария не пустой."""
        super().clean()
        self.text = normalize_text(self.text)
        if not self.text:
            message = 'Текст комментария не может быть пустым.'
            raise ValidationError({'text': message})
