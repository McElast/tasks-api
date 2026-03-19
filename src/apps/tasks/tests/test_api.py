"""Тесты REST API приложения задач."""

from collections.abc import Callable

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from ..enums import TaskStatus
from ..models import Task

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_jwt_token_can_be_obtained(
    api_client: APIClient,
    user: User,
    login_credentials: dict[str, str],
) -> None:
    """Проверяет получение JWT-токена."""
    response = api_client.post('/api/auth/jwt/create/', data=login_credentials, format='json')

    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.json()
    assert 'refresh' in response.json()


def test_task_can_be_created_via_api(
    auth_api_client: APIClient,
    api_task_payload: Callable[..., dict[str, object]],
) -> None:
    """Проверяет создание задачи через API."""
    response = auth_api_client.post('/api/tasks/', data=api_task_payload(), format='json')

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()['title'] == 'Подготовить API релиз'
    assert Task.objects.filter(title='Подготовить API релиз').exists()


def test_task_list_is_filtered_by_visible_tasks(
    auth_api_client: APIClient,
    second_user: User,
    outsider: User,
    task: Task,
) -> None:
    """Проверяет фильтрацию списка задач по доступу пользователя."""
    Task.objects.create(
        title='Чужая задача',
        description='Не должна попасть в выборку.',
        author=outsider,
        assignee=None,
        status=TaskStatus.NEW,
    )

    response = auth_api_client.get('/api/tasks/')

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]['id'] == task.pk


def test_task_detail_is_available_for_author(auth_api_client: APIClient, task: Task) -> None:
    """Проверяет просмотр детальной задачи через API."""
    response = auth_api_client.get(f'/api/tasks/{task.pk}/')

    assert response.status_code == status.HTTP_200_OK
    assert response.json()['id'] == task.pk


def test_task_update_works_for_author(
    auth_api_client: APIClient,
    task: Task,
    api_task_payload: Callable[..., dict[str, object]],
) -> None:
    """Проверяет обновление задачи автором."""
    response = auth_api_client.patch(
        f'/api/tasks/{task.pk}/',
        data=api_task_payload(title='Обновлённая задача', status=TaskStatus.DONE),
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()['status'] == TaskStatus.DONE
    assert response.json()['is_completed'] is True


def test_task_delete_is_forbidden_for_assignee(second_auth_api_client: APIClient, task: Task) -> None:
    """Проверяет запрет на удаление задачи исполнителем."""
    response = second_auth_api_client.delete(f'/api/tasks/{task.pk}/')

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_task_delete_works_for_author(auth_api_client: APIClient, task: Task) -> None:
    """Проверяет удаление задачи автором."""
    task_id = task.pk
    response = auth_api_client.delete(f'/api/tasks/{task.pk}/')

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Task.objects.filter(pk=task_id).exists()


def test_complete_and_reopen_actions_work(auth_api_client: APIClient, task: Task) -> None:
    """Проверяет кастомные действия complete и reopen."""
    complete_response = auth_api_client.post(f'/api/tasks/{task.pk}/complete/')
    reopen_response = auth_api_client.post(f'/api/tasks/{task.pk}/reopen/')

    assert complete_response.status_code == status.HTTP_200_OK
    assert complete_response.json()['status'] == TaskStatus.DONE
    assert reopen_response.status_code == status.HTTP_200_OK
    assert reopen_response.json()['status'] == TaskStatus.IN_PROGRESS


def test_comments_can_be_created_and_listed(auth_api_client: APIClient, task: Task) -> None:
    """Проверяет создание и чтение комментариев через API."""
    create_response = auth_api_client.post(
        f'/api/tasks/{task.pk}/comments/',
        data={'text': 'Комментарий из API'},
        format='json',
    )
    list_response = auth_api_client.get(f'/api/tasks/{task.pk}/comments/')

    assert create_response.status_code == status.HTTP_201_CREATED
    assert create_response.json()['text'] == 'Комментарий из API'
    assert list_response.status_code == status.HTTP_200_OK
    assert len(list_response.json()) == 1


def test_foreign_task_access_returns_forbidden(api_client: APIClient, outsider: User, task: Task) -> None:
    """Проверяет возврат 403 при доступе к чужой задаче."""
    api_client.force_authenticate(user=outsider)

    response = api_client.get(f'/api/tasks/{task.pk}/')

    assert response.status_code == status.HTTP_403_FORBIDDEN
