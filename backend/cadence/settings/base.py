from celery.schedules import crontab

from .environment import env, repo_root

REPO_ROOT = repo_root()

SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

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
    "apps.core.apps.CoreConfig",
    "apps.boards.apps.BoardsConfig",
    "apps.weeks.apps.WeeksConfig",
    "apps.tasks.apps.TasksConfig",
    "apps.jobs.apps.JobsConfig",
    "apps.imports.apps.ImportsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.telegram_bot.apps.TelegramBotConfig",
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
    "default": env.db("DATABASE_URL"),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = env("CADENCE_TIME_ZONE")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = REPO_ROOT / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = REPO_ROOT / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.core.authentication.ApiKeyAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.core.permissions.IsSessionAuthenticatedOrApiKey",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Cadence API",
    "VERSION": "1.0.0",
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_BEAT_SCHEDULE = {
    "scan-json-inbox": {
        "task": "apps.imports.tasks.scan_json_inbox",
        "schedule": crontab(minute="*/1"),
    },
    "scan-reminders": {
        "task": "apps.notifications.tasks.scan_reminders",
        "schedule": crontab(minute="*/5"),
    },
}

TELEGRAM_ENABLED = env("TELEGRAM_ENABLED")
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")

TASK_INBOX_PENDING_DIR = env("TASK_INBOX_PENDING_DIR")
TASK_INBOX_PROCESSING_DIR = env("TASK_INBOX_PROCESSING_DIR")
TASK_INBOX_PROCESSED_DIR = env("TASK_INBOX_PROCESSED_DIR")
TASK_INBOX_FAILED_DIR = env("TASK_INBOX_FAILED_DIR")
