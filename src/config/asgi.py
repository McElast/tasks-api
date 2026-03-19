"""ASGI-конфигурация проекта."""

import os
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application

from .settings.env import load_env_file

load_env_file(Path(__file__).resolve().parents[2] / '.env')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

django_application = get_asgi_application()
application = (
    ASGIStaticFilesHandler(django_application) if getattr(settings, 'SERVE_STATIC_FILES', False) else django_application
)
