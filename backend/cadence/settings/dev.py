from .base import *  # noqa: F403
from .environment import env

DEBUG: bool = env.bool("DJANGO_DEBUG", True)

CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
