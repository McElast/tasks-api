# Tasks App
Веб-приложение для управления задачами на Django 6.0.3 и Python 3.14.

Проект включает два интерфейса:
- HTML-приложение на Django Templates;
- REST API на Django REST Framework с JWT-аутентификацией и Swagger/OpenAPI.

Основной сценарий локальной разработки построен вокруг `uv`.

# Важные пояснения
- использован Django в асинхронном режиме
- запускать можно в условно дев-, прод-, тестовом режимах
- [locust-report-100.html](locust-report-100.html) - небольшой отчет по нагрузке для 100 пользователей
- основной упор сделан на бекенд-логике
- фронт-часть реализована с помощью шаблонов Джанго
- база SQLite для простоты
- реализованы типизации, проверка линтерами, тесты
- добавлены github-actions

## Стек технологий
- Python 3.14
- Django 6 (асинхронный)
- Django REST Framework
- djangorestframework-simplejwt
- drf-spectacular
- SQLite
- uv
- uvicorn
- pytest
- pytest-django
- pytest-asyncio
- ruff
- mypy

## Возможности
- создание, редактирование, удаление и просмотр задач;
- назначение исполнителя;
- завершение и повторное открытие задачи;
- комментарии к задачам;
- HTML-аутентификация через Django auth;
- JWT-аутентификация для API;
- Swagger UI и OpenAPI схемы;
- разграничение доступа по автору и исполнителю;
- фильтрация задач в HTML и API.

## Правила доступа
- с системой работают только авторизованные пользователи;
- пользователь видит только задачи, где он автор или исполнитель;
- автор и исполнитель могут просматривать и редактировать задачу;
- только автор может менять исполнителя;
- только автор может удалить задачу;
- комментировать задачу могут только пользователи с доступом к ней.

## Пояснения по структуре
- `apps.tasks.models` оформлен как пакет: каждая модель вынесена в отдельный модуль (`task.py`, `comment.py`), а 
пакетный `__init__.py` сохраняет единый публичный импорт;
- `apps.tasks.forms` оформлен так же: `TaskForm` и `CommentForm` живут в отдельных модулях, но импортируются через 
общий пакет;
- `apps.tasks.services` содержит бизнес-операции и централизованные проверки прав;
- `apps.tasks.selectors` отвечает за чтение и фильтрацию данных;
- HTML-представления и DRF-API используют общий сервисный слой;
- настройки разделены на `base`, `dev`, `test`, `prod`;
- проект готов к ASGI-запуску через `config.asgi`.

## Архитектурные решения и применённые паттерны
### Архитектурные решения
- слоистая структура: `views` / `api` / `forms` / `serializers` отделены от `services`, `selectors` и моделей;
- `models` и `forms` разбиты на пакеты с файлами по классам, чтобы доменные и UI-сущности не разрастались в одном модуле;
- разделение чтения и записи: чтение вынесено в `selectors`, а изменяющие операции - в `services`;
- единый use-case слой для HTML и API: бизнес-операции не дублируются между Django Templates и DRF;
- инварианты предметной области защищены на двух уровнях: в модели через `clean()` / `save()` и в БД через `CheckConstraint`;
- права доступа централизованы в сервисных проверках и переиспользуются в HTML views и API permissions;
- запись обёрнута в `transaction.atomic`, чтобы операции над задачами и комментариями были консистентными;
- настройки разделены по окружениям (`base`, `dev`, `test`, `prod`) для предсказуемого запуска и тестирования;
- API подготовлен к async-сценариям через локальную `AsyncAPIView`, совместимую с текущим стеком DRF.

### Паттерны
- `Service Layer`: `apps.tasks.services` инкапсулирует прикладные сценарии `create_task`, `update_task`, 
`complete_task`, `reopen_task`, `create_comment`;
- `Selector / Query Object`: `apps.tasks.selectors` инкапсулирует правила выборки и фильтрации задач, включая 
`select_related` / `prefetch_related`;
- `CQRS-lite`: чтение и запись разведены по разным модулям без введения отдельной шины команд и запросов;
- `Data Transfer Object`: `TaskUpdateData` используется как явный типизированный контракт для обновления задачи;
- `Rich Domain Model`: модель `Task` сама синхронизирует `status`, `is_completed` и `completed_at`, а не 
перекладывает это на views;
- `Transaction Script`: отдельные прикладные операции оформлены как явные транзакционные функции;
- `Policy-based authorization`: функции `can_*` и `assert_can_*` описывают правила доступа отдельно от 
транспортного слоя;
- `Adapter`: `AsyncAPIView` адаптирует стандартный `APIView` DRF под async-обработчики и смешанный sync/async lifecycle;
- `Mixin`: `TaskObjectPermissionMixin` переиспользует логику загрузки задачи и проверки объектных прав в нескольких 
API ручках.

## Структура проекта

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── .env.example
├── README.md
├── reff.md
├── TASK.md
├── pyproject.toml
├── uv.lock
├── static/
│   └── css/
│       └── styles.css
├── templates/
│   ├── base.html
│   ├── registration/
│   │   └── login.html
│   └── tasks/
│       ├── task_confirm_delete.html
│       ├── task_detail.html
│       ├── task_form.html
│       └── task_list.html
└── src/
    ├── manage.py
    ├── apps/
    │   └── tasks/
    │       ├── api/
    │       │   ├── async_api_view.py
    │       │   ├── async_support.py
    │       │   ├── mixins.py
    │       │   ├── permissions.py
    │       │   ├── serializers.py
    │       │   ├── urls.py
    │       │   ├── view_helpers.py
    │       │   └── views.py
    │       ├── forms/
    │       │   ├── comment_form.py
    │       │   └── task_form.py
    │       ├── migrations/
    │       │   ├── 0001_initial.py
    │       │   └── 0002_seed_initial_data.py
    │       ├── models/
    │       │   ├── comment.py
    │       │   └── task.py
    │       ├── tests/
    │       │   ├── conftest.py
    │       │   ├── test_api.py
    │       │   ├── test_models.py
    │       │   ├── test_services.py
    │       │   └── test_views.py
    │       ├── admin.py
    │       ├── apps.py
    │       ├── async_utils.py
    │       ├── enums.py
    │       ├── mixins.py
    │       ├── selectors.py
    │       ├── services.py
    │       ├── urls.py
    │       ├── validation.py
    │       ├── view_helpers.py
    │       └── views.py
    └── config/
        ├── settings/
        │   ├── base.py
        │   ├── dev.py
        │   ├── env.py
        │   ├── prod.py
        │   └── test.py
        ├── asgi.py
        ├── urls.py
        └── wsgi.py
```

## Как установить `uv`
Варианты установки:

- Linux/macOS:

```bash
python -m pip install uv
```

- Windows PowerShell:

```powershell
py -m pip install uv
```

- официальный установщик: `https://docs.astral.sh/uv/`

## Локальный запуск через `uv`
1. При необходимости скопируйте шаблон переменных окружения в корень проекта:

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

2. При запуске проект автоматически подгружает переменные из `.env`.
Если та же переменная уже задана в shell или в конфигурации IDE, приоритет остаётся за внешним окружением.
Файл `.env` теперь может задавать и `DJANGO_SETTINGS_MODULE`, потому что entrypoint'ы загружают его до выбора настроек.

3. Установите зависимости:

```bash
uv sync --group dev
```

4. Примените миграции:

```bash
uv run python src/manage.py migrate
```

5. Создайте суперпользователя:

```bash
uv run python src/manage.py createsuperuser
```

6. Запустите сервер разработки:

```bash
uv run python src/manage.py runserver
```

7. Откройте приложение:

- HTML: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`
- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`

## Предзаполненные данные
После `uv run python src/manage.py migrate` автоматически создаются демонстрационные данные:
- администратор:
  - username: `admin`
  - email: `admin@tasks.local`
  - password: `AdminPass123!`
- ещё 4 обычных пользователя + 8 задач + 9 комментариев.

## Production ASGI-подход
Вариант для production-подобного запуска:

1. Переключите проект на production-настройки.

В `.env`:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_SERVE_STATIC_FILES=True
```

2. При необходимости соберите статику:

```bash
uv run python src/manage.py collectstatic --noinput
```

3. Запустите ASGI-сервер:

```bash
uv run uvicorn config.asgi:application --app-dir src --host 0.0.0.0 --port 8000 --workers 4 --lifespan off
```

Замечание:
- количество воркеров подбирается по окружению;
- флаг `--lifespan off` убирает ожидаемое предупреждение `ASGI 'lifespan' protocol appears unsupported` для 
стандартного Django ASGI-приложения;
- `config.asgi` и `config.wsgi` умеют раздавать статику через Django staticfiles и при `DEBUG=False`, если 
  `DJANGO_SERVE_STATIC_FILES=True`; для настоящего production обычно лучше вынести статику в nginx/CDN;
- SQLite подходит для локального запуска, но не для нагруженного production.

## Основные маршруты

### HTML
- `GET /` - список задач;
- `GET /tasks/create/` - создание задачи;
- `GET /tasks/<id>/` - просмотр задачи;
- `GET /tasks/<id>/edit/` - редактирование задачи;
- `POST /tasks/<id>/complete/` - завершение;
- `POST /tasks/<id>/reopen/` - повторное открытие;
- `POST /tasks/<id>/comments/create/` - добавление комментария.

### API

Аутентификация:
- `POST /api/auth/jwt/create/`
- `POST /api/auth/jwt/refresh/`
- `POST /api/auth/jwt/verify/`

Пользователь:
- `GET /api/users/me/`

Задачи:
- `GET /api/tasks/`
- `POST /api/tasks/`
- `GET /api/tasks/<id>/`
- `PATCH /api/tasks/<id>/`
- `DELETE /api/tasks/<id>/`
- `POST /api/tasks/<id>/complete/`
- `POST /api/tasks/<id>/reopen/`
- `GET /api/tasks/<id>/comments/`
- `POST /api/tasks/<id>/comments/`

## Команды качества
Проверка Django:

```bash
uv run python src/manage.py check
```

Тесты:

```bash
uv run pytest
```

Линтер:

```bash
uv run ruff check .
```

Типизация:

```bash
uv run mypy src
```

Проверка миграций:

```bash
uv run python src/manage.py makemigrations --check --dry-run
```

## Куда дорабатывать
- фронт - на нативный фреймворк (React, Vue.js и т.п.)
- базу - MySQL или PostgreSQL
- докеризация (с разделением на прод-дев-тесты)
