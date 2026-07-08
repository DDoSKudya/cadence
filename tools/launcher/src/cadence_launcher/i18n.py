from __future__ import annotations

import json
import locale
import os
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir

APP_NAME = "cadence-launcher"
DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = frozenset({"en", "ru"})

_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "btn.start": "Start",
        "btn.stop": "Stop",
        "btn.open": "Open",
        "services.title": "Services",
        "loading.title": "Loading",
        "loading.check_env": "Checking environment…",
        "loading.read_status": "Reading service status…",
        "status.stopped": "Stopped",
        "status.running": "Running",
        "status.starting": "Starting…",
        "status.stopping": "Stopping…",
        "status.error": "Error: {message}",
        "activity.prep_stop": "Preparing to stop…",
        "activity.prep_start": "Preparing to start…",
        "activity.elapsed": "Elapsed {elapsed} s",
        "activity.elapsed_step": "{step} · {elapsed} s",
        "activity.stopping_services": "Stopping services…",
        "activity.starting_services": "Starting services…",
        "activity.stopped_count": "Stopped {stopped} of {total} services",
        "activity.ready_count": "Ready {ready} of {total} services",
        "activity.all_ready": "All services are ready",
        "activity.all_stopped": "All services are stopped",
        "activity.error": "Error",
        "msg.cadence_unavailable": "Cadence is unavailable",
        "msg.status_load_failed": "Failed to load status",
        "msg.browser_failed": "Failed to open browser",
        "msg.action_failed": "Operation failed",
        "msg.repo_not_found": "Could not find the Cadence repository automatically. Select its root folder.",
        "msg.invalid_folder": "Invalid folder",
        "dialog.select_repo": "Select Cadence root",
        "runtime.docker_missing": "Docker was not found in PATH.",
        "runtime.project_not_found": "Project not found: {path}",
        "runtime.invalid_repo": "The selected folder does not look like a Cadence root.",
        "runtime.already_running": "Cadence is already running",
        "runtime.unknown_state": "Cadence is in an unknown state. Stop services first.",
        "runtime.starting": "Starting Cadence…",
        "runtime.prep_stop": "Stopping existing services before start…",
        "runtime.start_failed": "Failed to start Cadence (code {code})",
        "runtime.start_retry": "Start failed — retrying…",
        "runtime.rollback": "Rolling back after failed start…",
        "runtime.already_stopped": "Cadence is already stopped",
        "runtime.stopping": "Stopping Cadence…",
        "runtime.stop_failed": "Failed to stop Cadence (code {code})",
        "runtime.timeout": "Timed out waiting for services to become ready.",
        "runtime.progress_ready": "Ready {ready} of {total} services",
        "runtime.all_ready": "All services are ready",
        "runtime.secret_required": (
            "Production start requires DJANGO_SECRET_KEY. "
            "Set it in .env or environment, or keep the value from .mise.toml."
        ),
        "runtime.secret_fallback": (
            "Warning: DJANGO_SECRET_KEY is not set; using the local production-like fallback from .mise.toml."
        ),
        "runtime.stop_scope": (
            "Stop affects the prod profile only. Dev containers started separately are not removed."
        ),
        "friendly.service_ready": "{name}: ready",
        "friendly.service_waiting": "{name}: waiting…",
        "friendly.service_starting": "{name}: starting…",
        "friendly.service_started": "{name}: started",
        "friendly.service_created": "{name}: created",
        "friendly.service_stopped": "{name}: stopped",
        "friendly.service_removing": "{name}: removing…",
        "friendly.building": "Building images…",
        "friendly.pulling": "Pulling images…",
        "friendly.creating": "Creating containers…",
        "friendly.starting_containers": "Starting containers…",
        "friendly.stopping_containers": "Stopping containers…",
        "friendly.checking_ready": "Checking readiness…",
        "friendly.api_ok": "API is available",
        "friendly.web_ok": "Web UI is available",
        "friendly.done": "Done",
    },
    "ru": {
        "btn.start": "Запустить",
        "btn.stop": "Остановить",
        "btn.open": "Открыть",
        "services.title": "Сервисы",
        "loading.title": "Загрузка",
        "loading.check_env": "Проверка окружения…",
        "loading.read_status": "Чтение статуса сервисов…",
        "status.stopped": "Остановлено",
        "status.running": "Работает",
        "status.starting": "Запускается…",
        "status.stopping": "Останавливается…",
        "status.error": "Ошибка: {message}",
        "activity.prep_stop": "Подготовка к остановке…",
        "activity.prep_start": "Подготовка к запуску…",
        "activity.elapsed": "Прошло {elapsed} с",
        "activity.elapsed_step": "{step} · {elapsed} с",
        "activity.stopping_services": "Остановка сервисов…",
        "activity.starting_services": "Запуск сервисов…",
        "activity.stopped_count": "Остановлено {stopped} из {total} сервисов",
        "activity.ready_count": "Готово {ready} из {total} сервисов",
        "activity.all_ready": "Все сервисы готовы",
        "activity.all_stopped": "Все сервисы остановлены",
        "activity.error": "Ошибка",
        "msg.cadence_unavailable": "Cadence недоступен",
        "msg.status_load_failed": "Не удалось загрузить статус",
        "msg.browser_failed": "Не удалось открыть браузер",
        "msg.action_failed": "Операция не выполнена",
        "msg.repo_not_found": "Не удалось автоматически найти репозиторий Cadence. Выберите его корневую папку.",
        "msg.invalid_folder": "Неверная папка",
        "dialog.select_repo": "Выберите корень Cadence",
        "runtime.docker_missing": "Docker не найден в PATH.",
        "runtime.project_not_found": "Проект не найден: {path}",
        "runtime.invalid_repo": "Выбранная папка не похожа на корень Cadence.",
        "runtime.already_running": "Cadence уже работает",
        "runtime.unknown_state": "Cadence запущен в неизвестном состоянии. Остановите сервисы.",
        "runtime.starting": "Запуск Cadence…",
        "runtime.prep_stop": "Остановка сервисов перед запуском…",
        "runtime.start_failed": "Не удалось запустить Cadence (код {code})",
        "runtime.start_retry": "Ошибка запуска — повторная попытка…",
        "runtime.rollback": "Откат после ошибки запуска…",
        "runtime.already_stopped": "Cadence уже остановлен",
        "runtime.stopping": "Остановка Cadence…",
        "runtime.stop_failed": "Не удалось остановить Cadence (код {code})",
        "runtime.timeout": "Превышено время ожидания готовности сервисов.",
        "runtime.progress_ready": "Готово {ready} из {total} сервисов",
        "runtime.all_ready": "Все сервисы готовы",
        "runtime.secret_required": (
            "Для production-запуска нужен DJANGO_SECRET_KEY. "
            "Задайте его в .env или окружении, либо оставьте значение из .mise.toml."
        ),
        "runtime.secret_fallback": (
            "Предупреждение: DJANGO_SECRET_KEY не задан; используется локальный production-like fallback из .mise.toml."
        ),
        "runtime.stop_scope": (
            "Остановка затрагивает только prod-профиль. Dev-контейнеры, запущенные отдельно, не удаляются."
        ),
        "friendly.service_ready": "{name}: готов",
        "friendly.service_waiting": "{name}: ожидание…",
        "friendly.service_starting": "{name}: запуск…",
        "friendly.service_started": "{name}: запущен",
        "friendly.service_created": "{name}: создан",
        "friendly.service_stopped": "{name}: остановлен",
        "friendly.service_removing": "{name}: удаление…",
        "friendly.building": "Сборка образов…",
        "friendly.pulling": "Загрузка образов…",
        "friendly.creating": "Создание контейнеров…",
        "friendly.starting_containers": "Запуск контейнеров…",
        "friendly.stopping_containers": "Остановка контейнеров…",
        "friendly.checking_ready": "Проверка готовности…",
        "friendly.api_ok": "API доступен",
        "friendly.web_ok": "Веб-интерфейс доступен",
        "friendly.done": "Готово",
    },
}

_current_locale = DEFAULT_LOCALE


def config_file_path() -> Path:
    return Path(user_config_dir(APP_NAME)) / "config.json"


def read_config_language() -> str | None:
    path = config_file_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    language = data.get("language")
    if isinstance(language, str) and language in SUPPORTED_LOCALES:
        return language
    return None


def detect_system_locale() -> str:
    for getter in (
        lambda: locale.getdefaultlocale()[0],
        lambda: locale.getlocale()[0],
    ):
        try:
            value = getter()
        except Exception:
            value = None
        if value and value.lower().startswith("ru"):
            return "ru"
    return DEFAULT_LOCALE


def resolve_locale(explicit: str | None = None) -> str:
    if explicit in SUPPORTED_LOCALES:
        return explicit
    env_lang = os.getenv("CADENCE_LAUNCHER_LANG", "").strip().lower()
    if env_lang in SUPPORTED_LOCALES:
        return env_lang
    saved = read_config_language()
    if saved:
        return saved
    return detect_system_locale()


def init_locale(explicit: str | None = None) -> str:
    global _current_locale
    _current_locale = resolve_locale(explicit)
    return _current_locale


def get_locale() -> str:
    return _current_locale


def set_locale(lang: str) -> str:
    global _current_locale
    if lang not in SUPPORTED_LOCALES:
        lang = DEFAULT_LOCALE
    _current_locale = lang
    return _current_locale


def tr(key: str, **kwargs: Any) -> str:
    table = _MESSAGES.get(_current_locale) or _MESSAGES[DEFAULT_LOCALE]
    template = table.get(key) or _MESSAGES[DEFAULT_LOCALE].get(key) or key
    if kwargs:
        return template.format(**kwargs)
    return template
