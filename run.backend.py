import os
import sys
from pathlib import Path
from django.core.management import execute_from_command_line


def main():
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
        bundle_dir = Path(getattr(sys, "_MEIPASS", base_dir)).resolve()
    else:
        base_dir = Path(__file__).resolve().parent
        bundle_dir = base_dir

    os.chdir(base_dir)

    sys.path.insert(0, str(base_dir))
    sys.path.insert(0, str(bundle_dir))

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "inventory_management_system.settings",
    )
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    execute_from_command_line([
        "manage.py",
        "runserver",
        "127.0.0.1:8000",
        "--noreload",
        "--nothreading",
    ])


if __name__ == "__main__":
    main()