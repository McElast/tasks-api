"""Тесты HTML-представлений приложения задач."""

from collections.abc import Callable

import pytest
from django.contrib.auth.models import User
from django.test import Client

from ..models import Comment, Task

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_login_page_allows_user_authentication(
    html_client: Client,
    user: User,
    login_credentials: dict[str, str],
) -> None:
    """Проверяет вход пользователя через стандартную форму авторизации."""
    response = html_client.post('/auth/login/', data=login_credentials)

    assert response.status_code == 302
    assert response.headers['Location'] == '/'


def test_task_list_requires_login(html_client: Client) -> None:
    """Проверяет, что список задач защищён авторизацией."""
    response = html_client.get('/')

    assert response.status_code == 302
    assert '/auth/login/' in response.headers['Location']


def test_task_can_be_created_via_form(
    authorized_html_client: Client,
    html_task_form_data: Callable[..., dict[str, object]],
) -> None:
    """Проверяет создание задачи через HTML-форму."""
    response = authorized_html_client.post('/tasks/create/', data=html_task_form_data())

    assert response.status_code == 302
    assert Task.objects.filter(title='Создать страницу отчёта').exists()


def test_task_can_be_updated_via_form(
    authorized_html_client: Client,
    task: Task,
    html_task_form_data: Callable[..., dict[str, object]],
) -> None:
    """Проверяет редактирование задачи через HTML-форму."""
    response = authorized_html_client.post(
        f'/tasks/{task.pk}/edit/',
        data=html_task_form_data(
            title='Исправленный заголовок',
            description=task.description,
            status='in_progress',
            assignee=task.assignee_id,
        ),
    )

    task.refresh_from_db()

    assert response.status_code == 302
    assert task.title == 'Исправленный заголовок'


def test_task_detail_displays_comments(authorized_html_client: Client, task: Task, comment: Comment) -> None:
    """Проверяет отображение комментариев на странице задачи."""
    response = authorized_html_client.get(f'/tasks/{task.pk}/')

    assert response.status_code == 200
    assert 'Первый комментарий' in response.content.decode('utf-8')


def test_delete_is_forbidden_for_non_author(html_client: Client, second_user: User, task: Task) -> None:
    """Проверяет ограничение на удаление задачи неавтором."""
    html_client.force_login(second_user)

    response = html_client.post(f'/tasks/{task.pk}/delete/')

    assert response.status_code == 403
