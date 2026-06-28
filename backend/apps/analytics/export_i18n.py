from __future__ import annotations

from apps.common.i18n import DEFAULT_LOCALE, get_locale

SUPPORTED_LOCALES = frozenset({"en", "ru"})

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "export.reportTitle": "Cadence Analytics",
        "export.report.tasks": "Tasks report",
        "export.report.archive": "Archive report",
        "export.report.weekly_summary": "Weekly summary",
        "export.report.tag_summary": "Tag summary",
        "export.report.notification_report": "Notifications report",
        "export.report.jobs_report": "Background jobs report",
        "export.report.imports_report": "Imports report",
        "export.generatedAt": "Generated",
        "export.scheme": "Scheme",
        "export.period": "Period",
        "export.periodAll": "All time",
        "export.periodWeek": "Week {week}",
        "export.periodRange": "{start} — {end}",
        "export.sheet.overview": "Overview",
        "export.sheet.tasks": "Tasks",
        "export.sheet.archive": "Archive",
        "export.sheet.summary": "Weekly trend",
        "export.sheet.byTags": "By tags",
        "export.sheet.byColumns": "By columns",
        "export.sheet.staleTasks": "Stale tasks",
        "export.sheet.tags": "Tags",
        "export.sheet.notifications": "Notifications",
        "export.sheet.jobs": "Background jobs",
        "export.sheet.imports": "Imports",
        "export.col.id": "ID",
        "export.col.title": "Title",
        "export.col.column": "Column",
        "export.col.systemType": "Column type",
        "export.col.week": "Week",
        "export.col.tags": "Tags",
        "export.col.source": "Source",
        "export.col.dueAt": "Due date",
        "export.col.createdAt": "Created",
        "export.col.closedAt": "Closed",
        "export.col.archivedAt": "Archived",
        "export.col.completionNote": "Completion note",
        "export.col.created": "Created",
        "export.col.closed": "Closed",
        "export.col.carriedOver": "Carry-over",
        "export.col.count": "Count",
        "export.col.tag": "Tag",
        "export.col.daysInColumn": "Days in column",
        "export.col.taskId": "Task ID",
        "export.col.taskTitle": "Task title",
        "export.col.status": "Status",
        "export.col.reason": "Reason",
        "export.col.telegramChat": "Telegram chat",
        "export.col.scheduledAt": "Scheduled",
        "export.col.sentAt": "Sent",
        "export.col.failedAt": "Failed",
        "export.col.lastError": "Last error",
        "export.col.jobType": "Job type",
        "export.col.attempts": "Attempts",
        "export.col.startedAt": "Started",
        "export.col.finishedAt": "Finished",
        "export.col.filename": "Filename",
        "export.col.tasksCreated": "Tasks created",
        "export.col.sourceLabel": "Source label",
        "export.col.errorMessage": "Error",
        "export.kpi.created": "Created",
        "export.kpi.closed": "Closed",
        "export.kpi.active": "Active",
        "export.kpi.overdue": "Overdue",
        "export.kpi.stale": "Stale",
        "export.table.noData": "No data found for the selected filters.",
        "export.meta.brand": "Cadence Analytics",
        "export.footnote": "Report layout: title, metadata, table, and chart.",
        "export.total": "total",
        "export.chart.weeklyTrend": "Weekly dynamics",
        "export.chart.byTags": "Distribution by tags",
        "export.chart.byColumns": "Distribution by columns",
        "export.chart.columnDistribution": "Tasks by column",
        "export.chart.closedByWeek": "Closed by week",
        "export.chart.tagDistribution": "Distribution by tags",
        "export.chart.notificationStatus": "Notifications by status",
        "export.chart.jobStatus": "Jobs by status",
        "export.chart.importStatus": "Imports by status",
        "export.chart.telegramActions": "Telegram actions",
        "export.source.ui": "UI",
        "export.source.api": "API",
        "export.source.json_import": "JSON import",
        "export.source.telegram": "Telegram",
        "export.source.system": "System",
        "export.column.backlog": "Backlog",
        "export.column.planned": "Planned",
        "export.column.in_progress": "In progress",
        "export.column.blocked": "Blocked",
        "export.column.review": "Review",
        "export.column.ready": "Ready",
        "export.column.done": "Done",
        "export.status.open": "Open",
        "export.status.ready_on_develop": "Ready on develop",
        "export.status.process": "In progress",
        "export.status.testing": "Testing",
        "export.status.done": "Done",
        "export.status.cancel": "Cancelled",
    },
    "ru": {
        "export.reportTitle": "Cadence — аналитика",
        "export.report.tasks": "Отчёт по задачам",
        "export.report.archive": "Отчёт по архиву",
        "export.report.weekly_summary": "Сводка по неделям",
        "export.report.tag_summary": "Отчёт по тегам",
        "export.report.notification_report": "Отчёт по оповещениям",
        "export.report.jobs_report": "Отчёт по фоновым задачам",
        "export.report.imports_report": "Отчёт по импортам",
        "export.generatedAt": "Сформирован",
        "export.scheme": "Схема",
        "export.period": "Период",
        "export.periodAll": "За всё время",
        "export.periodWeek": "Неделя {week}",
        "export.periodRange": "{start} — {end}",
        "export.sheet.overview": "Обзор",
        "export.sheet.tasks": "Задачи",
        "export.sheet.archive": "Архив",
        "export.sheet.summary": "Динамика по неделям",
        "export.sheet.byTags": "По тегам",
        "export.sheet.byColumns": "По колонкам",
        "export.sheet.staleTasks": "Застрявшие задачи",
        "export.sheet.tags": "Теги",
        "export.sheet.notifications": "Оповещения",
        "export.sheet.jobs": "Фоновые задачи",
        "export.sheet.imports": "Импорты",
        "export.col.id": "ID",
        "export.col.title": "Название",
        "export.col.column": "Колонка",
        "export.col.systemType": "Тип колонки",
        "export.col.week": "Неделя",
        "export.col.tags": "Теги",
        "export.col.source": "Источник",
        "export.col.dueAt": "Срок",
        "export.col.createdAt": "Создана",
        "export.col.closedAt": "Закрыта",
        "export.col.archivedAt": "В архиве",
        "export.col.completionNote": "Заметка о закрытии",
        "export.col.created": "Создано",
        "export.col.closed": "Закрыто",
        "export.col.carriedOver": "Перенос",
        "export.col.count": "Количество",
        "export.col.tag": "Тег",
        "export.col.daysInColumn": "Дней в колонке",
        "export.col.taskId": "ID задачи",
        "export.col.taskTitle": "Задача",
        "export.col.status": "Статус",
        "export.col.reason": "Причина",
        "export.col.telegramChat": "Чат Telegram",
        "export.col.scheduledAt": "Запланировано",
        "export.col.sentAt": "Отправлено",
        "export.col.failedAt": "Ошибка",
        "export.col.lastError": "Текст ошибки",
        "export.col.jobType": "Тип задачи",
        "export.col.attempts": "Попытки",
        "export.col.startedAt": "Начато",
        "export.col.finishedAt": "Завершено",
        "export.col.filename": "Файл",
        "export.col.tasksCreated": "Создано задач",
        "export.col.sourceLabel": "Метка источника",
        "export.col.errorMessage": "Ошибка",
        "export.kpi.created": "Создано",
        "export.kpi.closed": "Закрыто",
        "export.kpi.active": "Активные",
        "export.kpi.overdue": "Просрочено",
        "export.kpi.stale": "Застряли",
        "export.table.noData": "Данные не найдены по выбранным фильтрам.",
        "export.meta.brand": "Cadence Analytics",
        "export.footnote": "Структура отчёта: заголовок, метаданные, таблица и график.",
        "export.total": "всего",
        "export.chart.weeklyTrend": "Динамика по неделям",
        "export.chart.byTags": "Распределение по тегам",
        "export.chart.byColumns": "Распределение по колонкам",
        "export.chart.columnDistribution": "Задачи по колонкам",
        "export.chart.closedByWeek": "Закрыто по неделям",
        "export.chart.tagDistribution": "Распределение по тегам",
        "export.chart.notificationStatus": "Оповещения по статусу",
        "export.chart.jobStatus": "Фоновые задачи по статусу",
        "export.chart.importStatus": "Импорты по статусу",
        "export.chart.telegramActions": "Действия в Telegram",
        "export.source.ui": "UI",
        "export.source.api": "API",
        "export.source.json_import": "JSON-импорт",
        "export.source.telegram": "Telegram",
        "export.source.system": "Система",
        "export.column.backlog": "Бэклог",
        "export.column.planned": "План",
        "export.column.in_progress": "В работе",
        "export.column.blocked": "Блокер",
        "export.column.review": "Проверка",
        "export.column.ready": "Готово",
        "export.column.done": "Закрыто",
        "export.status.open": "Открыта",
        "export.status.ready_on_develop": "Готова к работе",
        "export.status.process": "В работе",
        "export.status.testing": "Тестирование",
        "export.status.done": "Выполнена",
        "export.status.cancel": "Отменена",
    },
}


def resolve_export_locale(payload: dict | None) -> str:
    if payload:
        locale = str(payload.get("locale", "")).strip().lower()
        if locale in SUPPORTED_LOCALES:
            return locale
    return get_locale()


def et(key: str, *, locale: str, **kwargs: object) -> str:
    resolved = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    text = MESSAGES.get(resolved, MESSAGES[DEFAULT_LOCALE]).get(key)
    if text is None:
        text = MESSAGES[DEFAULT_LOCALE].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def translate_column(locale: str, system_type: str, name: str) -> str:
    if system_type:
        label = et(f"export.column.{system_type}", locale=locale)
        if label != f"export.column.{system_type}":
            return label
    return name


def translate_source(locale: str, source: str) -> str:
    key = f"export.source.{source}"
    label = et(key, locale=locale)
    return label if label != key else source


def translate_status(locale: str, slug: str) -> str:
    key = f"export.status.{slug}"
    label = et(key, locale=locale)
    return label if label != key else slug
