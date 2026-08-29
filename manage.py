#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# Auto-include local venv site-packages if running directly with system python
BASE_DIR = Path(__file__).resolve().parent
for venv_path in [BASE_DIR / 'venv', BASE_DIR.parent / 'venv', BASE_DIR / '.venv', BASE_DIR.parent / '.venv']:
    if venv_path.exists():
        win_site = venv_path / 'Lib' / 'site-packages'
        if win_site.exists() and str(win_site) not in sys.path:
            sys.path.insert(0, str(win_site))
        lib_dir = venv_path / 'lib'
        if lib_dir.exists():
            for py_dir in lib_dir.glob('python*'):
                site_pkg = py_dir / 'site-packages'
                if site_pkg.exists() and str(site_pkg) not in sys.path:
                    sys.path.insert(0, str(site_pkg))


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()

