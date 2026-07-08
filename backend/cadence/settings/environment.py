"""Environment variables for Django settings."""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT_DEFAULT = str(BACKEND_DIR.parent)
_INBOX_ROOT_DEFAULT = str(Path(_REPO_ROOT_DEFAULT) / "data" / "task-inbox")

env = environ.Env(
    DJANGO_SECRET_KEY=(str, "change-me"),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CADENCE_REPO_ROOT=(str, _REPO_ROOT_DEFAULT),
    CADENCE_TIME_ZONE=(str, "Europe/Moscow"),
    LOG_LEVEL=(str, "INFO"),
    CADENCE_LOG_DIR=(str, f"{_REPO_ROOT_DEFAULT}/logs"),
    CADENCE_SERVICE_NAME=(str, "api"),
    CSRF_TRUSTED_ORIGINS=(list, []),
    DATABASE_URL=(str, "postgres://cadence:cadence@localhost:5432/cadence"),
    CELERY_BROKER_URL=(str, "amqp://cadence:cadence@localhost:5672//"),
    TELEGRAM_ENABLED=(bool, False),
    TELEGRAM_BOT_TOKEN=(str, ""),
    TASK_INBOX_PENDING_DIR=(str, f"{_INBOX_ROOT_DEFAULT}/pending"),
    TASK_INBOX_PROCESSING_DIR=(str, f"{_INBOX_ROOT_DEFAULT}/processing"),
    TASK_INBOX_PROCESSED_DIR=(str, f"{_INBOX_ROOT_DEFAULT}/processed"),
    TASK_INBOX_FAILED_DIR=(str, f"{_INBOX_ROOT_DEFAULT}/failed"),
)

env_file = BACKEND_DIR.parent / ".env"
example_env_file = BACKEND_DIR.parent / ".env.example"
if env_file.exists():
    env.read_env(env_file)
elif example_env_file.exists():
    env.read_env(example_env_file)

if env.str("DJANGO_SETTINGS_MODULE", "").endswith(".prod"):
    secret_key = env("DJANGO_SECRET_KEY")
    if not secret_key or secret_key == "change-me":
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be configured explicitly in production.",
        )


def repo_root() -> Path:
    return Path(env.str("CADENCE_REPO_ROOT", _REPO_ROOT_DEFAULT))
