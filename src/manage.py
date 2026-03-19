#!/usr/bin/env python
"""Точка входа для административных команд Django."""

import os
import sys
from pathlib import Path

from config.settings.env import load_env_file


def main() -> None:
    """Запускает административную команду Django."""
    load_env_file(Path(__file__).resolve().parents[1] / '.env')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as error:
        message = 'Django не установлен или недоступен в текущем окружении.'
        raise ImportError(message) from error
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
