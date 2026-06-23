from datetime import datetime

import pytest

from apps.common.i18n import format_notification_due_at, get_locale, t
from apps.core.models import ProjectSettings


@pytest.mark.django_db
def test_i18n_defaults_to_english():
    settings = ProjectSettings.load()
    settings.language = ProjectSettings.Language.EN
    settings.save(update_fields=["language", "updated_at"])
    assert get_locale() == "en"
    assert t("telegram.button.done") == "Done"


@pytest.mark.django_db
def test_i18n_russian_locale():
    settings = ProjectSettings.load()
    settings.language = ProjectSettings.Language.RU
    settings.save(update_fields=["language", "updated_at"])
    assert get_locale() == "ru"
    assert t("telegram.button.done") == "Выполнено"


def test_i18n_explicit_locale_overrides_project_settings():
    assert t("telegram.button.done", locale="ru") == "Выполнено"
    assert t("telegram.button.done", locale="en") == "Done"


def test_i18n_format_notification_due_at_by_locale():
    value = datetime(2025, 6, 23, 14, 30)
    assert format_notification_due_at(value, locale="en") == "06/23/2025 14:30"
    assert format_notification_due_at(value, locale="ru") == "23.06.2025 14:30"
