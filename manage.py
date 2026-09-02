#!/usr/bin/env python
"""Utilidad de linea de comandos de Django para PL_SGE."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No fue posible importar Django. Verifique la instalacion y el entorno virtual: "
            "pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
