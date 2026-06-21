from django.contrib import admin

from apps.imports.models import ImportLog


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = (
        "filename",
        "status",
        "tasks_created",
        "idempotency_key",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("filename", "idempotency_key", "checksum")
    readonly_fields = (
        "filename",
        "original_path",
        "checksum",
        "idempotency_key",
        "schema_version",
        "source_label",
        "status",
        "tasks_created",
        "error_message",
        "started_at",
        "finished_at",
        "created_at",
    )
