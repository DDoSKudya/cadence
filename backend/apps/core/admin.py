from collections.abc import Sequence
from typing import ClassVar

from django.contrib import admin, messages

from apps.core.models import ApiKey, ProjectSettings, Tag


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "prefix", "is_active", "last_used_at", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "prefix")
    readonly_fields = ("prefix", "key_hash", "last_used_at", "created_at")

    def get_fields(self, request, obj=None):
        if obj:
            return ("name", "is_active", "prefix", "last_used_at", "created_at")
        return ("name",)

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return

        _api_key, raw_key = ApiKey.issue(obj.name)
        self.message_user(
            request,
            f"API key created. Copy it now, it will not be shown again: {raw_key}",
            messages.WARNING,
        )


@admin.register(ProjectSettings)
class ProjectSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "timezone",
        "json_inbox_enabled",
        "telegram_enabled",
        "telegram_bot_username",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return not ProjectSettings.objects.exists()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields: ClassVar[dict[str, Sequence[str]]] = {"slug": ("name",)}
