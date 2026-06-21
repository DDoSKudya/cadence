from collections.abc import Sequence
from typing import ClassVar

from django.contrib import admin

from apps.boards.models import Board, BoardColumn


class BoardColumnInline(admin.TabularInline):
    model = BoardColumn
    extra = 0
    fields = ("name", "system_type", "color", "position", "is_active", "wip_limit")
    ordering = ("position",)


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_default", "updated_at")
    list_filter = ("is_default",)
    search_fields = ("name", "slug")
    prepopulated_fields: ClassVar[dict[str, Sequence[str]]] = {"slug": ("name",)}
    inlines = (BoardColumnInline,)


@admin.register(BoardColumn)
class BoardColumnAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "board",
        "system_type",
        "position",
        "color",
        "is_active",
        "wip_limit",
    )
    list_filter = ("board", "system_type", "is_active")
    search_fields = ("name",)
    ordering = ("board", "position")
