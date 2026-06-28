from .base import *  # noqa: F403
from .environment import env

DEBUG: bool = env.bool("DJANGO_DEBUG", True)

# Run Celery tasks in-process during local development so export code changes
# apply immediately without restarting the worker container.
CELERY_TASK_ALWAYS_EAGER = DEBUG
CELERY_TASK_EAGER_PROPAGATES = True

CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
