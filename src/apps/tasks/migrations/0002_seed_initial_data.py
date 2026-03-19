"""Data migration с администратором и демонстрационными данными."""


from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.db import migrations
from django.utils import timezone

ADMIN_USERNAME = 'admin'
ADMIN_EMAIL = 'admin@tasks.local'
ADMIN_PASSWORD = 'AdminPass123!'

SEED_USERS = [
    {
        'username': 'olga',
        'email': 'olga@tasks.local',
        'first_name': 'Ольга',
        'last_name': 'Соколова',
        'password': 'OlgaPass123!',
    },
    {
        'username': 'ivan',
        'email': 'ivan@tasks.local',
        'first_name': 'Иван',
        'last_name': 'Петров',
        'password': 'IvanPass123!',
    },
    {
        'username': 'anna',
        'email': 'anna@tasks.local',
        'first_name': 'Анна',
        'last_name': 'Миронова',
        'password': 'AnnaPass123!',
    },
    {
        'username': 'maksim',
        'email': 'maksim@tasks.local',
        'first_name': 'Максим',
        'last_name': 'Крылов',
        'password': 'MaksimPass123!',
    },
]

SEED_TASKS = [
    {
        'title': 'Подготовить демо для заказчика',
        'description': 'Собрать рабочий сценарий и проверить все ключевые переходы.',
        'status': 'in_progress',
        'is_completed': False,
        'completed_delta_days': None,
        'author': 'olga',
        'assignee': 'ivan',
    },
    {
        'title': 'Обновить базу знаний команды',
        'description': 'Добавить краткие инструкции по запуску, тестам и типизации.',
        'status': 'new',
        'is_completed': False,
        'completed_delta_days': None,
        'author': 'admin',
        'assignee': 'anna',
    },
    {
        'title': 'Проверить сценарии прав доступа',
        'description': 'Пройти позитивные и негативные сценарии для автора и исполнителя.',
        'status': 'done',
        'is_completed': True,
        'completed_delta_days': 3,
        'author': 'ivan',
        'assignee': 'maksim',
    },
    {
        'title': 'Согласовать контент для лендинга',
        'description': 'Уточнить тексты карточек и статусы для демонстрационного стенда.',
        'status': 'in_progress',
        'is_completed': False,
        'completed_delta_days': None,
        'author': 'anna',
        'assignee': 'olga',
    },
    {
        'title': 'Разобрать обратную связь QA',
        'description': 'Собрать замечания после тестового прогона и определить приоритеты.',
        'status': 'done',
        'is_completed': True,
        'completed_delta_days': 1,
        'author': 'maksim',
        'assignee': 'admin',
    },
    {
        'title': 'Подготовить заметки к релизу',
        'description': 'Сформировать краткий список изменений для внутренней рассылки.',
        'status': 'new',
        'is_completed': False,
        'completed_delta_days': None,
        'author': 'admin',
        'assignee': None,
    },
    {
        'title': 'Упростить форму создания задачи',
        'description': 'Проверить понятность подписей и улучшить текст подсказок.',
        'status': 'in_progress',
        'is_completed': False,
        'completed_delta_days': None,
        'author': 'olga',
        'assignee': 'anna',
    },
    {
        'title': 'Сверить Swagger со схемой API',
        'description': 'Проверить, что кастомные действия и JWT отражены в документации.',
        'status': 'done',
        'is_completed': True,
        'completed_delta_days': 2,
        'author': 'admin',
        'assignee': 'ivan',
    },
]

SEED_COMMENTS = [
    {
        'task_title': 'Подготовить демо для заказчика',
        'author': 'olga',
        'text': 'Собрала структуру сценария, осталось проверить финальные тексты.',
    },
    {
        'task_title': 'Подготовить демо для заказчика',
        'author': 'ivan',
        'text': 'Подтяну примеры задач и комментариев к вечернему созвону.',
    },
    {
        'task_title': 'Обновить базу знаний команды',
        'author': 'anna',
        'text': 'Добавлю отдельный блок про команды `uv run` и fallback без `uv`.',
    },
    {
        'task_title': 'Проверить сценарии прав доступа',
        'author': 'maksim',
        'text': 'Негативные сценарии для удаления и чужих задач уже подтверждены.',
    },
    {
        'task_title': 'Согласовать контент для лендинга',
        'author': 'olga',
        'text': 'Нужен ещё один проход по заголовкам карточек на мобильном.',
    },
    {
        'task_title': 'Разобрать обратную связь QA',
        'author': 'admin',
        'text': 'Критичных блокеров нет, но стоит упростить тексты ошибок.',
    },
    {
        'task_title': 'Подготовить заметки к релизу',
        'author': 'admin',
        'text': 'Черновик релиз-заметок создан, жду финальный список изменений.',
    },
    {
        'task_title': 'Упростить форму создания задачи',
        'author': 'anna',
        'text': 'Подсказка для исполнителя теперь понятнее, но стоит сократить текст.',
    },
    {
        'task_title': 'Сверить Swagger со схемой API',
        'author': 'ivan',
        'text': 'Схема открывается, кастомные `complete` и `reopen` отображаются.',
    },
]


def seed_initial_data(apps, schema_editor) -> None:
    """Создаёт администратора, пользователей, задачи и комментарии для демонстрации."""
    User = apps.get_model('auth', 'User')
    Task = apps.get_model('tasks', 'Task')
    Comment = apps.get_model('tasks', 'Comment')

    admin_user, _ = User.objects.update_or_create(
        username=ADMIN_USERNAME,
        defaults={
            'email': ADMIN_EMAIL,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'first_name': 'Администратор',
            'last_name': 'Проекта',
            'password': make_password(ADMIN_PASSWORD),
        },
    )

    users_by_username = {ADMIN_USERNAME: admin_user}
    for user_data in SEED_USERS:
        user, _ = User.objects.update_or_create(
            username=user_data['username'],
            defaults={
                'email': user_data['email'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'is_active': True,
                'password': make_password(user_data['password']),
            },
        )
        users_by_username[user.username] = user

    now = timezone.now()
    tasks_by_title = {}
    for index, task_data in enumerate(SEED_TASKS):
        completed_at = None
        if task_data['is_completed'] and task_data['completed_delta_days'] is not None:
            completed_at = now - timedelta(days=task_data['completed_delta_days'])
        task, _ = Task.objects.update_or_create(
            title=task_data['title'],
            author=users_by_username[task_data['author']],
            defaults={
                'description': task_data['description'],
                'status': task_data['status'],
                'assignee': users_by_username.get(task_data['assignee']),
                'is_completed': task_data['is_completed'],
                'completed_at': completed_at,
                'created_at': now - timedelta(days=12 - index),
                'updated_at': now - timedelta(days=max(0, 6 - index)),
            },
        )
        tasks_by_title[task.title] = task

    for comment_data in SEED_COMMENTS:
        Comment.objects.update_or_create(
            task=tasks_by_title[comment_data['task_title']],
            author=users_by_username[comment_data['author']],
            text=comment_data['text'],
        )


def remove_seed_initial_data(apps, schema_editor) -> None:
    """Удаляет пользователей и демонстрационные сущности, созданные миграцией."""
    User = apps.get_model('auth', 'User')
    Task = apps.get_model('tasks', 'Task')
    Comment = apps.get_model('tasks', 'Comment')

    Comment.objects.filter(text__in=[comment['text'] for comment in SEED_COMMENTS]).delete()
    Task.objects.filter(title__in=[task['title'] for task in SEED_TASKS]).delete()
    User.objects.filter(username__in=[ADMIN_USERNAME, *(user['username'] for user in SEED_USERS)]).delete()


class Migration(migrations.Migration):
    """Миграция заполнения проекта начальными демонстрационными данными."""

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_initial_data, remove_seed_initial_data),
    ]
