"""Сериализаторы REST API для задач и комментариев."""

from collections.abc import Callable
from typing import Any

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from ..enums import TaskStatus
from ..models import Comment, Task
from ..services import TaskUpdateData, create_task, update_task
from ..validation import coerce_task_status, normalize_text


class UserSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Краткий сериализатор пользователя."""

    class Meta:
        """Мета-настройки сериализатора пользователя."""

        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class CommentSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Сериализатор комментариев задачи."""

    author = UserSerializer(read_only=True)

    class Meta:
        """Мета-настройки сериализатора комментария."""

        model = Comment
        fields = ['id', 'author', 'text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    @staticmethod
    def validate_text(value: str) -> str:
        """Проверяет непустой текст комментария."""
        value = normalize_text(value)
        if not value:
            raise serializers.ValidationError('Текст комментария не может быть пустым.')
        return value


class TaskSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Сериализатор задач для чтения и записи."""

    author = UserSerializer(read_only=True)
    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        source='assignee',
        queryset=User.objects.order_by('username'),
        required=False,
        allow_null=True,
        write_only=True,
    )
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        """Мета-настройки сериализатора задачи."""

        model = Task
        fields = [
            'id',
            'title',
            'description',
            'status',
            'author',
            'assignee',
            'assignee_id',
            'is_completed',
            'completed_at',
            'created_at',
            'updated_at',
            'comments',
        ]
        read_only_fields = ['id', 'author', 'assignee', 'is_completed', 'completed_at', 'created_at', 'updated_at']

    def _request_user(self) -> User:
        """Возвращает типизированного пользователя из request context."""
        user = self.context['request'].user
        if not isinstance(user, User):
            raise TypeError('TaskSerializer requires authenticated django.contrib.auth User.')
        return user

    @staticmethod
    def _coerce_assignee(value: Any) -> User | None:
        """Возвращает исполнителя в ожидаемом типе или поднимает ошибку типов."""
        if value is None or isinstance(value, User):
            return value
        raise TypeError('TaskSerializer expects assignee to be django.contrib.auth User or None.')

    @staticmethod
    def _handle_django_validation(
        operation: Callable[..., Task],
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Task:
        """Преобразует Django ValidationError в DRF ValidationError."""
        try:
            return operation(*args, **kwargs)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

    @staticmethod
    def _task_update_data(instance: Task, validated_data: dict[str, Any]) -> TaskUpdateData:
        """Собирает payload обновления задачи из partial validated_data."""
        return TaskUpdateData(
            title=str(validated_data.get('title', instance.title)),
            description=str(validated_data.get('description', instance.description)),
            status=coerce_task_status(validated_data.get('status'), default=TaskStatus(instance.status)),
            assignee=TaskSerializer._coerce_assignee(validated_data.get('assignee', instance.assignee)),
        )

    def create(self, validated_data: dict[str, Any]) -> Task:
        """Создаёт задачу через сервисный слой."""
        return self._handle_django_validation(
            create_task,
            actor=self._request_user(),
            title=str(validated_data['title']),
            description=str(validated_data.get('description', '')),
            assignee=self._coerce_assignee(validated_data.get('assignee')),
            status=coerce_task_status(validated_data.get('status'), default=TaskStatus.NEW),
        )

    def update(self, instance: Task, validated_data: dict[str, Any]) -> Task:
        """Обновляет задачу через сервисный слой."""
        return self._handle_django_validation(
            update_task,
            actor=self._request_user(),
            task=instance,
            data=self._task_update_data(instance, validated_data),
        )

    @staticmethod
    def validate_title(value: str) -> str:
        """Проверяет непустой заголовок задачи."""
        value = normalize_text(value)
        if not value:
            raise serializers.ValidationError('Заголовок задачи не может быть пустым.')
        return value
