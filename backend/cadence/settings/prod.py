from .base import *  # noqa: F403
from .environment import env

DEBUG: bool = env.bool("DJANGO_DEBUG", False)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
