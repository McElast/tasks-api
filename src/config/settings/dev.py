"""Настройки для локальной разработки."""

from . import apply_module_settings
from . import base as base_settings

apply_module_settings(globals(), base_settings)

DEBUG = True
