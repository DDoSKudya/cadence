from django.contrib import admin

from apps.notifications.models import NotificationJob, TelegramCallbackLog


@admin.register(NotificationJob)
class NotificationJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "task",
        "reason",
        "status",
        "scheduled_at",
        "sent_at",
        "created_at",
    )
    list_filter = ("status", "reason")
    search_fields = ("task__title", "dedup_key", "telegram_chat_id")
    readonly_fields = (
        "task",
        "background_job",
        "dedup_key",
        "message_id",
        "sent_at",
        "failed_at",
        "created_at",
    )


@admin.register(TelegramCallbackLog)
class TelegramCallbackLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action",
        "task",
        "telegram_user_id",
        "processed_at",
        "created_at",
    )
    list_filter = ("action",)
    search_fields = ("callback_query_id", "telegram_user_id")
    readonly_fields = ("created_at", "processed_at")
