from django.contrib import admin

from apps.tasks.models import Task, TaskEvent


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "column",
        "week",
        "priority",
        "position",
        "source",
        "archived_at",
    )
    list_filter = ("column", "priority", "source", "archived_at")
    search_fields = ("title", "description")
    ordering = ("column", "position")


@admin.register(TaskEvent)
class TaskEventAdmin(admin.ModelAdmin):
    list_display = ("task", "event_type", "actor_type", "source", "created_at")
    list_filter = ("event_type", "actor_type", "source")
    ordering = ("-created_at",)
