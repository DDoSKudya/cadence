from collections.abc import Mapping, Sequence
from typing import TypedDict

from rest_framework import serializers

from apps.boards.models import Board, BoardColumn
from apps.core.serializers import TagSerializer
from apps.tasks.models import Task, TaskEvent, TaskLinkType, TaskPriority, TaskType
from apps.tasks.task_link_services import TaskLinkService
from apps.weeks.models import Week
from apps.weeks.serializers import WeekSerializer


class BoardPayload(TypedDict):
    board: Board
    week: Week
    columns: Sequence[BoardColumn]
    tasks_by_column: Mapping[int, list[Task]]


class TaskLinkWriteSerializer(serializers.Serializer):
    target_task_id = serializers.IntegerField(min_value=1)
    link_type = serializers.ChoiceField(choices=TaskLinkType.choices)


class TaskBoardSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    task_status_id = serializers.IntegerField(read_only=True, allow_null=True)
    task_status_name = serializers.SerializerMethodField()
    links_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "task_type",
            "priority",
            "position",
            "column_id",
            "week_id",
            "due_at",
            "source",
            "story_points",
            "tags",
            "task_status_id",
            "task_status_name",
            "links_count",
        )

    def get_task_status_name(self, obj: Task) -> str | None:
        status = obj.task_status
        return status.name if status is not None else None

    def get_links_count(self, obj: Task) -> int:
        outgoing = getattr(obj, "_outgoing_links_count", None)
        incoming = getattr(obj, "_incoming_links_count", None)
        if outgoing is not None and incoming is not None:
            return int(outgoing) + int(incoming)
        return TaskLinkService.link_count(obj)


class TaskSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    week = WeekSerializer(read_only=True)
    task_status_id = serializers.IntegerField(read_only=True, allow_null=True)
    task_status = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "board_id",
            "column_id",
            "week",
            "week_id",
            "position",
            "task_type",
            "priority",
            "column_entered_at",
            "due_at",
            "source",
            "external_ref",
            "story_points",
            "completion_note",
            "reminder_enabled",
            "next_reminder_at",
            "last_notified_at",
            "reminder_interval_minutes",
            "created_by_id",
            "created_at",
            "updated_at",
            "closed_at",
            "archived_at",
            "tags",
            "task_status_id",
            "task_status",
            "links",
        )
        read_only_fields = (
            "id",
            "board_id",
            "column_id",
            "position",
            "column_entered_at",
            "source",
            "created_by_id",
            "created_at",
            "updated_at",
            "closed_at",
            "archived_at",
            "next_reminder_at",
            "last_notified_at",
            "task_status_id",
            "task_status",
            "links",
        )

    def get_task_status(self, obj: Task) -> dict[str, object] | None:
        if obj.task_status_id is None:
            return None
        status = obj.task_status
        if status is None:
            return None
        return {
            "id": status.id,
            "name": status.name,
            "slug": status.slug,
            "color": status.color,
        }

    def get_links(self, obj: Task) -> list[dict[str, object]]:
        return TaskLinkService.serialize_for_task(obj)


class TaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    column_id = serializers.IntegerField(required=False)
    week = serializers.CharField(required=False, allow_null=True)
    task_type = serializers.ChoiceField(choices=TaskType.choices)
    priority = serializers.ChoiceField(
        choices=TaskPriority.choices,
        required=False,
        default=TaskPriority.NORMAL,
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=60),
        required=False,
        allow_empty=True,
    )
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    reminder_enabled = serializers.BooleanField(required=False, default=True)
    story_points = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=99,
    )
    external_ref = serializers.CharField(required=False, allow_blank=True, default="")
    links = TaskLinkWriteSerializer(many=True, required=False, allow_empty=True)


class TaskUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    week = serializers.CharField(required=False, allow_null=True)
    task_type = serializers.ChoiceField(choices=TaskType.choices, required=False)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, required=False)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=60),
        required=False,
        allow_empty=True,
    )
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    reminder_enabled = serializers.BooleanField(required=False)
    reminder_interval_minutes = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
    )
    story_points = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=99,
    )
    external_ref = serializers.CharField(required=False, allow_blank=True)
    task_status_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True
    )
    links = TaskLinkWriteSerializer(many=True, required=False, allow_empty=True)


class TaskMoveSerializer(serializers.Serializer):
    target_column_id = serializers.IntegerField()
    target_position = serializers.IntegerField(min_value=0)


class TaskCloseSerializer(serializers.Serializer):
    completion_note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class TaskEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskEvent
        fields = (
            "id",
            "event_type",
            "actor_type",
            "actor_id",
            "source",
            "payload",
            "created_at",
        )


class BoardResponseSerializer(serializers.Serializer):
    board = serializers.SerializerMethodField()
    week = serializers.SerializerMethodField()
    columns = serializers.SerializerMethodField()

    def get_board(self, payload: BoardPayload) -> dict[str, int | str | bool]:
        board = payload["board"]
        return {
            "id": board.id,
            "name": board.name,
            "is_default": board.is_default,
        }

    def get_week(self, payload: BoardPayload) -> dict[str, int]:
        week = payload["week"]
        return {
            "id": week.id,
            "iso_year": week.iso_year,
            "iso_week": week.iso_week,
        }

    def get_columns(self, payload: BoardPayload) -> list[dict[str, object]]:
        tasks_by_column = payload["tasks_by_column"]
        result = []
        for column in payload["columns"]:
            tasks = tasks_by_column.get(column.id, [])
            result.append(
                {
                    "id": column.id,
                    "name": column.name,
                    "system_type": column.system_type,
                    "position": column.position,
                    "color": column.color,
                    "wip_limit": column.wip_limit,
                    "is_locked": column.is_locked,
                    "tasks": TaskBoardSerializer(tasks, many=True).data,
                },
            )
        return result
