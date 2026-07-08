from __future__ import annotations

from cadence_launcher.friendly_action import friendly_action_line
from cadence_launcher.i18n import init_locale, set_locale, tr


def test_default_locale_is_english() -> None:
    init_locale("en")
    assert tr("btn.start") == "Start"
    assert tr("btn.stop") == "Stop"


def test_russian_locale() -> None:
    set_locale("ru")
    assert tr("btn.start") == "Запустить"
    assert tr("services.title") == "Сервисы"


def test_friendly_action_line_is_localized() -> None:
    set_locale("en")
    assert friendly_action_line("Building images") == "Building images…"
    set_locale("ru")
    assert friendly_action_line("Building images") == "Сборка образов…"


def test_runtime_message_formatting() -> None:
    set_locale("en")
    assert tr("runtime.progress_ready", ready=2, total=6) == "Ready 2 of 6 services"
    set_locale("ru")
    assert tr("runtime.progress_ready", ready=2, total=6) == "Готово 2 из 6 сервисов"
