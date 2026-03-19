"""Общие фикстуры для тестов приложения задач."""

from collections.abc import Callable

import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.test import APIClient

from ..enums import TaskStatus
from ..models import Comment, Task

TEST_PASSWORD = 'test-password'


def _create_user(*, username: str) -> User:
    """Создаёт пользователя для тестов."""
    return User.objects.create_user(username=username, password=TEST_PASSWORD)


@pytest.fixture
def user(db: object) -> User:
    """Создаёт основного пользователя для тестов."""
    return _create_user(username='author')


@pytest.fixture
def second_user(db: object) -> User:
    """Создаёт второго пользователя для тестов."""
    return _create_user(username='assignee')


@pytest.fixture
def outsider(db: object) -> User:
    """Создаёт пользователя без доступа к тестовой задаче."""
    return _create_user(username='outsider')


@pytest.fixture
def task(user: User, second_user: User) -> Task:
    """Создаёт базовую задачу для тестов."""
    return Task.objects.create(
        title='Подготовить демо',
        description='Нужно собрать рабочий сценарий.',
        author=user,
        assignee=second_user,
        status=TaskStatus.IN_PROGRESS,
    )


@pytest.fixture
def comment(task: Task, user: User) -> Comment:
    """Создаёт базовый комментарий для тестов."""
    return Comment.objects.create(task=task, author=user, text='Первый комментарий')


@pytest.fixture
def login_credentials() -> dict[str, str]:
    """Возвращает логин и пароль автора для тестов аутентификации."""
    return {'username': 'author', 'password': TEST_PASSWORD}


@pytest.fixture
def html_task_form_data(second_user: User) -> Callable[..., dict[str, object]]:
    """Возвращает фабрику POST-данных для HTML-формы задачи."""

    def builder(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            'title': 'Создать страницу отчёта',
            'description': 'Нужен HTML-сценарий для заказчика.',
            'status': 'new',
            'assignee': second_user.pk,
        }
        payload.update(overrides)
        return payload

    return builder


@pytest.fixture
def api_task_payload(second_user: User) -> Callable[..., dict[str, object]]:
    """Возвращает фабрику JSON-данных для API задачи."""

    def builder(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            'title': 'Подготовить API релиз',
            'description': 'Проверить схему и права доступа.',
            'status': TaskStatus.NEW,
            'assignee_id': second_user.pk,
        }
        payload.update(overrides)
        return payload

    return builder


@pytest.fixture
def api_client() -> APIClient:
    """Возвращает неавторизованный API-клиент."""
    return APIClient()


@pytest.fixture
def auth_api_client(user: User) -> APIClient:
    """Возвращает авторизованный API-клиент автора задачи."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def second_auth_api_client(second_user: User) -> APIClient:
    """Возвращает авторизованный API-клиент исполнителя задачи."""
    client = APIClient()
    client.force_authenticate(user=second_user)
    return client


@pytest.fixture
def html_client() -> Client:
    """Возвращает HTML-клиент Django."""
    return Client()


@pytest.fixture
def authorized_html_client(user: User) -> Client:
    """Возвращает HTML-клиент, авторизованный под автором задачи."""
    client = Client()
    client.force_login(user)
    return client
