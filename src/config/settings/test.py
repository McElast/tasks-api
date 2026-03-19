"""Настройки для тестового окружения."""

from . import apply_module_settings
from . import base as base_settings

apply_module_settings(globals(), base_settings)

DEBUG = False
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DATABASES = base_settings.DATABASES.copy()
DATABASES['default'] = {**base_settings.DATABASES['default'], 'NAME': base_settings.BASE_DIR / 'test_db.sqlite3'}
