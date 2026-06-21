from django.contrib import admin

from apps.jobs.models import BackgroundJob


@admin.register(BackgroundJob)
class BackgroundJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "job_type",
        "status",
        "attempts",
        "celery_task_id",
        "created_at",
    )
    list_filter = ("job_type", "status")
    search_fields = ("celery_task_id", "last_error")
    readonly_fields = (
        "job_type",
        "status",
        "payload",
        "result",
        "attempts",
        "max_attempts",
        "scheduled_at",
        "started_at",
        "finished_at",
        "last_error",
        "celery_task_id",
        "created_at",
        "updated_at",
    )
