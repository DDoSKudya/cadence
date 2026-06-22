from django.core.management.base import BaseCommand

from apps.telegram_bot.bot import run_telegram_async
from apps.telegram_bot.polling import run_polling


class Command(BaseCommand):
    help = "Run Telegram bot polling (callbacks and /start)"

    def handle(self, *args, **options) -> None:
        self.stdout.write("Starting Telegram bot polling...")
        run_telegram_async(run_polling())
