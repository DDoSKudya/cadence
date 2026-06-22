from typing import Any

from rest_framework import serializers

from apps.core.serializers import TagSerializer
from apps.tasks.models import Task, TaskEvent
from apps.tasks.serializers import TaskEventSerializer, TaskSerializer
from apps.weeks.serializers import WeekSerializer


class ArchiveTaskListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    week = WeekSerializer(read_only=True)
    column_name = serializers.CharField(source="column.name", read_only=True)
    column_system_type = serializers.CharField(
        source="column.system_type",
        read_only=True,
    )

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "column_id",
            "column_name",
            "column_system_type",
            "week",
            "week_id",
            "priority",
            "source",
            "completion_note",
            "evidence_url",
            "closed_at",
            "archived_at",
            "tags",
        )


class ArchiveTaskDetailSerializer(serializers.Serializer):
    def to_representation(self, instance: Task) -> dict[str, Any]:
        data = dict(TaskSerializer(instance).data)
        data["column_name"] = instance.column.name
        data["column_system_type"] = instance.column.system_type
        events = TaskEvent.objects.filter(task=instance).order_by("-created_at")
        data["events"] = TaskEventSerializer(events, many=True).data
        return data
