from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
                    text="Выполнено",
                    callback_data=f"{CallbackAction.TASK_DONE}:{suffix}",
                ),
                InlineKeyboardButton(
                    text="В процессе",
                    callback_data=f"{CallbackAction.TASK_IN_PROGRESS}:{suffix}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Отложить",
                    callback_data=f"{CallbackAction.TASK_SNOOZE}:{suffix}",
                ),
                InlineKeyboardButton(
                    text="Отключить",
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
    is_group = chat_type in ("group", "supergroup", "channel")
    kind_label = "Группа" if is_group else "Личный чат"
    recipient_kind = "group" if is_group else "user"

    lines = [
        "Cadence — оповещения о задачах",
        "",
        f"Chat ID: <code>{chat_id}</code>",
        f"Тип: {kind_label}",
        "",
        "Добавьте этот Chat ID в Cadence:",
        "Настройки → Оповещение → Telegram → Получатели.",
        f"Тип получателя: «{kind_label}» ({recipient_kind}).",
    ]
    if not is_group:
        lines.append("")
        lines.append("Для личных оповещений достаточно этого ID.")
    else:
        lines.append("")
        lines.append("Бот должен быть участником группы, чтобы отправлять сообщения.")
    return "\n".join(lines)
