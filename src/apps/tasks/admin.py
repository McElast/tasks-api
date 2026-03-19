"""Настройки административного интерфейса для задач."""

from django.contrib import admin

from .models import Comment, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Административное представление задач."""

    list_display = ('id', 'title', 'status', 'author', 'assignee', 'is_completed', 'created_at')
    list_filter = ('status', 'is_completed', 'created_at')
    search_fields = ('title', 'description', 'author__username', 'assignee__username')
    autocomplete_fields = ('author', 'assignee')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Административное представление комментариев."""

    list_display = ('id', 'task', 'author', 'created_at')
    search_fields = ('text', 'author__username', 'task__title')
    autocomplete_fields = ('task', 'author')
