from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BASE_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    TELEGRAM_ENABLED=(bool, False),
)

for env_file in (ROOT_DIR / ".env", ROOT_DIR / ".env.example"):
    if env_file.exists():
        env.read_env(env_file)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.common.apps.CommonConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cadence.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cadence.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://cadence:cadence@localhost:5432/cadence",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = env("CADENCE_TIME_ZONE", default="Europe/Moscow")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = ROOT_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = ROOT_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Cadence API",
    "VERSION": "1.0.0",
}

CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default="amqp://cadence:cadence@localhost:5672//",
)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

TELEGRAM_ENABLED = env("TELEGRAM_ENABLED")
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_DEFAULT_CHAT_ID = env("TELEGRAM_DEFAULT_CHAT_ID", default="")

TASK_INBOX_PENDING_DIR = env(
    "TASK_INBOX_PENDING_DIR",
    default=str(ROOT_DIR / "data" / "task-inbox" / "pending"),
)
TASK_INBOX_PROCESSING_DIR = env(
    "TASK_INBOX_PROCESSING_DIR",
    default=str(ROOT_DIR / "data" / "task-inbox" / "processing"),
)
TASK_INBOX_PROCESSED_DIR = env(
    "TASK_INBOX_PROCESSED_DIR",
    default=str(ROOT_DIR / "data" / "task-inbox" / "processed"),
)
TASK_INBOX_FAILED_DIR = env(
    "TASK_INBOX_FAILED_DIR",
    default=str(ROOT_DIR / "data" / "task-inbox" / "failed"),
)
