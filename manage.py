#!/usr/bin/env python
"""Django management utility."""
import os
import sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Django not found. Run: pip install -r requirements.txt") from exc
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
