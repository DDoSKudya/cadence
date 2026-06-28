from contextlib import suppress

from aiogram import Dispatcher, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from asgiref.sync import sync_to_async

from apps.common.i18n import t
from apps.notifications.actions import TelegramActionError, TelegramActionService
from apps.telegram_bot.bot import build_start_reply, get_bot, parse_callback_data

router = Router()

CALLBACK_STATUS_KEYS = {
    "closed": "telegram.callback.status.closed",
    "in_progress": "telegram.callback.status.inProgress",
    "status_updated": "telegram.callback.status.updated",
    "snoozed": "telegram.callback.status.snoozed",
    "reminders_cancelled": "telegram.callback.status.remindersCancelled",
    "already_closed": "telegram.callback.status.alreadyClosed",
    "duplicate": "telegram.callback.status.duplicate",
}


def callback_status_label(status: str) -> str:
    key = CALLBACK_STATUS_KEYS.get(status, "telegram.callback.status.default")
    return t(key)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    if message.chat is None:
        return

    text = build_start_reply(chat_id=message.chat.id, chat_type=message.chat.type)
    await message.answer(text, parse_mode="HTML")


@router.callback_query()
async def handle_callback(callback: CallbackQuery) -> None:
    if callback.data is None or callback.from_user is None:
        await callback.answer(t("telegram.callback.invalidRequest"))
        return

    try:
        action, task_id, notification_job_id, status_id = parse_callback_data(
            callback.data,
        )
    except ValueError:
        await callback.answer(t("telegram.callback.invalidRequest"))
        return

    try:
        result = await sync_to_async(TelegramActionService.handle_callback)(
            callback_query_id=callback.id,
            chat_id=str(callback.message.chat.id if callback.message else ""),
            telegram_user_id=str(callback.from_user.id),
            action=action,
            task_id=task_id,
            notification_job_id=notification_job_id,
            status_id=status_id,
        )
    except TelegramActionError:
        await callback.answer(t("telegram.callback.processingError"), show_alert=True)
        return

    status = str(result.get("status", ""))
    label = callback_status_label(status)
    await callback.answer(label, show_alert=status in {"closed", "already_closed"})

    if isinstance(callback.message, Message) and status not in {"duplicate"}:
        original = callback.message.text or callback.message.caption or ""
        footer = f"\n\n— {label}"
        if footer.strip() not in original:
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(
                    f"{original}{footer}",
                    reply_markup=None,
                    parse_mode="HTML",
                )


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return dispatcher


async def run_polling() -> None:
    bot = await sync_to_async(get_bot)()
    dispatcher = create_dispatcher()
    await dispatcher.start_polling(bot)
