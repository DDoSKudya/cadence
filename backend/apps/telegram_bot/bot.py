from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from apps.common.i18n import t
from apps.notifications.models import CallbackAction


def get_bot() -> Bot:
    from apps.core.models import ProjectSettings

    token = ProjectSettings.load().resolve_telegram_bot_token()
    if not token:
        raise RuntimeError("Telegram bot token is not configured")
    return Bot(token=token)


def run_telegram_async(coro):
    import asyncio

    return asyncio.run(coro)


def build_task_keyboard(task_id: int, notification_job_id: int) -> InlineKeyboardMarkup:
    suffix = f"{task_id}:{notification_job_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("telegram.button.done"),
                    callback_data=f"{CallbackAction.TASK_DONE}:{suffix}",
                ),
                InlineKeyboardButton(
                    text=t("telegram.button.inProgress"),
                    callback_data=f"{CallbackAction.TASK_IN_PROGRESS}:{suffix}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("telegram.button.snooze"),
                    callback_data=f"{CallbackAction.TASK_SNOOZE}:{suffix}",
                ),
                InlineKeyboardButton(
                    text=t("telegram.button.disableReminders"),
                    callback_data=f"{CallbackAction.TASK_CANCEL_REMINDERS}:{suffix}",
                ),
            ],
        ],
    )


def parse_callback_data(data: str) -> tuple[str, int, int | None]:
    parts = data.split(":")
    if len(parts) < 2:
        raise ValueError("Invalid callback data")

    action = parts[0]
    task_id = int(parts[1])
    notification_job_id = int(parts[2]) if len(parts) > 2 and parts[2] else None
    return action, task_id, notification_job_id


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
