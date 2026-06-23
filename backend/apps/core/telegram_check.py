from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from apps.common.i18n import t
from apps.core.models import ProjectSettings


@dataclass(frozen=True)
class TelegramBotCheckResult:
    ok: bool
    message: str
    checked_at: datetime
    bot_username: str | None = None


def check_telegram_bot(token: str) -> TelegramBotCheckResult:
    checked_at = timezone.now()
    if not token.strip():
        return TelegramBotCheckResult(
            ok=False,
            message=t("telegram.check.tokenMissing"),
            checked_at=checked_at,
        )

    async def _fetch_me():
        from aiogram import Bot

        bot = Bot(token=token.strip())
        try:
            return await bot.get_me()
        finally:
            await bot.session.close()

    try:
        me = asyncio.run(_fetch_me())
    except Exception as exc:
        return TelegramBotCheckResult(
            ok=False,
            message=str(exc)[:255],
            checked_at=checked_at,
        )

    username = me.username or ""
    return TelegramBotCheckResult(
        ok=True,
        message=f"@{username}" if username else t("telegram.check.botAvailable"),
        checked_at=checked_at,
        bot_username=username or None,
    )


def persist_telegram_bot_check(
    settings_obj: ProjectSettings,
    result: TelegramBotCheckResult,
) -> ProjectSettings:
    settings_obj.telegram_bot_check_ok = result.ok
    settings_obj.telegram_bot_check_message = result.message
    settings_obj.telegram_bot_checked_at = result.checked_at
    update_fields = [
        "telegram_bot_check_ok",
        "telegram_bot_check_message",
        "telegram_bot_checked_at",
    ]
    if (
        result.ok
        and result.bot_username
        and not settings_obj.telegram_bot_username.strip()
    ):
        settings_obj.telegram_bot_username = f"@{result.bot_username}"
        update_fields.append("telegram_bot_username")
    settings_obj.save(update_fields=update_fields)
    return settings_obj


def run_telegram_bot_check(
    settings_obj: ProjectSettings,
    *,
    token: str | None = None,
) -> TelegramBotCheckResult:
    resolved = (token or "").strip() or settings_obj.resolve_telegram_bot_token()
    result = check_telegram_bot(resolved)
    persist_telegram_bot_check(settings_obj, result)
    return result
