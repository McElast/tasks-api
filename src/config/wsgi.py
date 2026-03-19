"""WSGI-конфигурация проекта."""

import os
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application

from .settings.env import load_env_file

load_env_file(Path(__file__).resolve().parents[2] / '.env')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

django_application = get_wsgi_application()
application = (
    StaticFilesHandler(django_application) if getattr(settings, 'SERVE_STATIC_FILES', False) else django_application
)
