from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from apps.boards.task_status_services import TaskStatusService
from apps.common.i18n import t
from apps.notifications.models import CallbackAction
from apps.tasks.models import Task


def get_bot() -> Bot:
    from apps.core.models import ProjectSettings

    token = ProjectSettings.load().resolve_telegram_bot_token()
    if not token:
        raise RuntimeError("Telegram bot token is not configured")
    return Bot(token=token)


def run_telegram_async(coro):
    import asyncio

    return asyncio.run(coro)


def build_task_keyboard(task: Task, notification_job_id: int) -> InlineKeyboardMarkup:
    source_status = task.task_status
    if source_status is None:
        source_status = TaskStatusService.resolve_column_status(task.column)

    targets = TaskStatusService.list_allowed_targets(
        board=task.board,
        from_status=source_status,
    )

    rows: list[list[InlineKeyboardButton]] = []
    status_row: list[InlineKeyboardButton] = []
    for target in targets[:6]:
        status_row.append(
            InlineKeyboardButton(
                text=target.name,
                callback_data=(
                    f"{CallbackAction.TASK_SET_STATUS}:"
                    f"{task.id}:{target.id}:{notification_job_id}"
                ),
            ),
        )
        if len(status_row) == 2:
            rows.append(status_row)
            status_row = []
    if status_row:
        rows.append(status_row)

    rows.append(
        [
            InlineKeyboardButton(
                text=t("telegram.button.snooze"),
                callback_data=f"{CallbackAction.TASK_SNOOZE}:{task.id}:{notification_job_id}",
            ),
            InlineKeyboardButton(
                text=t("telegram.button.disableReminders"),
                callback_data=(
                    f"{CallbackAction.TASK_CANCEL_REMINDERS}:{task.id}:{notification_job_id}"
                ),
            ),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def parse_callback_data(data: str) -> tuple[str, int, int | None, int | None]:
    parts = data.split(":")
    if len(parts) < 2:
        raise ValueError("Invalid callback data")

    action = parts[0]
    task_id = int(parts[1])
    if action == CallbackAction.TASK_SET_STATUS:
        if len(parts) < 4:
            raise ValueError("Invalid callback data")
        status_id = int(parts[2])
        set_status_job_id = int(parts[3])
        return action, task_id, set_status_job_id, status_id

    optional_job_id = int(parts[2]) if len(parts) > 2 and parts[2] else None
    return action, task_id, optional_job_id, None


def build_start_reply(*, chat_id: int, chat_type: str) -> str:
    is_group = chat_type in {"group", "supergroup", "channel"}
    kind_key = (
        "telegram.recipientKind.group" if is_group else "telegram.recipientKind.private"
    )
    kind_label = t(kind_key)
    recipient_kind = "group" if is_group else "user"

    lines = [
        t("telegram.start.title"),
        "",
        t("telegram.start.chatId", chat_id=chat_id),
        t("telegram.start.type", kind=kind_label),
        "",
        t("telegram.start.instructions"),
        t("telegram.start.recipientPath"),
        t(
            "telegram.start.recipientType",
            kind=kind_label,
            kind_code=recipient_kind,
        ),
        "",
    ]
    if not is_group:
        lines.append(t("telegram.start.privateHint"))
    else:
        lines.append(t("telegram.start.groupHint"))
    return "\n".join(lines)
