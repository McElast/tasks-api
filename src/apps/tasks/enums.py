"""Наборы перечислений для задач."""

from django.db import models


class TaskStatus(models.TextChoices):
    """Перечисление возможных статусов задачи."""

    NEW = 'new', 'Новая'
    IN_PROGRESS = 'in_progress', 'В работе'
    DONE = 'done', 'Завершена'
