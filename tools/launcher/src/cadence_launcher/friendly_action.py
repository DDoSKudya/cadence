from __future__ import annotations

import re

from .i18n import tr


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text).strip()


def service_name_from_line(text: str) -> str | None:
    lowered = text.lower()
    if "cadence-" not in lowered:
        return None
    start = lowered.index("cadence-") + len("cadence-")
    rest = text[start:]
    return rest.split()[0].removesuffix("-1").replace("-", " ")


def friendly_action_line(line: str) -> str:
    text = strip_ansi(line)
    if not text:
        return ""

    lowered = text.lower()

    if lowered.startswith("[") and ("█" in text or "░" in text):
        return ""

    name = service_name_from_line(text)

    if name:
        if any(word in lowered for word in ("healthy", "здоров", "готов", "ready")):
            return tr("friendly.service_ready", name=name)
        if "waiting" in lowered or "ожидан" in lowered:
            return tr("friendly.service_waiting", name=name)
        if "starting" in lowered or "запуск" in lowered:
            return tr("friendly.service_starting", name=name)
        if "started" in lowered or "запущен" in lowered:
            return tr("friendly.service_started", name=name)
        if "created" in lowered or "создан" in lowered:
            return tr("friendly.service_created", name=name)
        if "stopped" in lowered or "exited" in lowered or "останов" in lowered:
            return tr("friendly.service_stopped", name=name)
        if "removing" in lowered or "удал" in lowered:
            return tr("friendly.service_removing", name=name)

    if "building" in lowered or "сборк" in lowered:
        return tr("friendly.building")
    if "pulling" in lowered or "pull complete" in lowered:
        return tr("friendly.pulling")
    if "creating" in lowered and "container" in lowered:
        return tr("friendly.creating")
    if "запуск cadence" in lowered or "starting cadence" in lowered:
        return tr("friendly.starting_containers")
    if "остановка cadence" in lowered or "stopping cadence" in lowered:
        return tr("friendly.stopping_containers")
    if (
        "ожидание готовности" in lowered
        or "ждём готовности" in lowered
        or "waiting for readiness" in lowered
    ):
        return tr("friendly.checking_ready")
    if (
        "все сервисы готовы" in lowered
        or "сервисы запущены" in lowered
        or "all services are ready" in lowered
    ):
        return tr("runtime.all_ready")
    if "все сервисы остановлены" in lowered or "all services are stopped" in lowered:
        return tr("activity.all_stopped")
    if "api:" in lowered and "ok" in lowered:
        return tr("friendly.api_ok")
    if "web:" in lowered and "ok" in lowered:
        return tr("friendly.web_ok")
    if lowered in {"готово", "done"}:
        return tr("friendly.done")

    if len(text) > 48:
        return text[:45] + "…"
    return text
