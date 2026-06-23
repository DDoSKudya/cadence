from __future__ import annotations

from datetime import datetime

from apps.common.i18n.messages import MESSAGES

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = frozenset(MESSAGES)


def get_locale() -> str:
    from apps.core.models import ProjectSettings

    language = ProjectSettings.load().language
    if language in SUPPORTED_LOCALES:
        return language
    return DEFAULT_LOCALE


def t(key: str, *, locale: str | None = None, **kwargs: object) -> str:
    resolved_locale = locale if locale in SUPPORTED_LOCALES else get_locale()
    text = MESSAGES.get(resolved_locale, MESSAGES[DEFAULT_LOCALE]).get(key)
    if text is None:
        text = MESSAGES[DEFAULT_LOCALE].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def format_notification_due_at(value: datetime, *, locale: str | None = None) -> str:
    resolved_locale = locale if locale in SUPPORTED_LOCALES else get_locale()
    localized = value
    if value.tzinfo is not None:
        from django.utils import timezone

        localized = timezone.localtime(value)
    if resolved_locale == "ru":
        return localized.strftime("%d.%m.%Y %H:%M")
    return localized.strftime("%m/%d/%Y %H:%M")
