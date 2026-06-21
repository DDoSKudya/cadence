from collections.abc import Mapping, Sequence
from typing import TypedDict

from rest_framework import serializers

from apps.boards.models import Board, BoardColumn
from apps.core.serializers import TagSerializer
from apps.tasks.models import Task, TaskEvent, TaskPriority
from apps.weeks.models import Week
from apps.weeks.serializers import WeekSerializer


class BoardPayload(TypedDict):
    board: Board
    week: Week
    columns: Sequence[BoardColumn]
    tasks_by_column: Mapping[int, list[Task]]


class TaskBoardSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "priority",
            "position",
            "column_id",
            "week_id",
            "due_at",
            "source",
            "tags",
        )


class TaskSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    week = WeekSerializer(read_only=True)

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
            "priority",
            "column_entered_at",
            "due_at",
            "source",
            "external_ref",
            "evidence_url",
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
        )


class TaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    column_id = serializers.IntegerField(required=False)
    week = serializers.CharField(required=False, allow_null=True)
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
    evidence_url = serializers.CharField(required=False, allow_blank=True, default="")
    reminder_enabled = serializers.BooleanField(required=False, default=True)


class TaskUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    week = serializers.CharField(required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, required=False)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=60),
        required=False,
        allow_empty=True,
    )
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    evidence_url = serializers.CharField(required=False, allow_blank=True)
    reminder_enabled = serializers.BooleanField(required=False)
    reminder_interval_minutes = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
    )


class TaskMoveSerializer(serializers.Serializer):
    target_column_id = serializers.IntegerField()
    target_position = serializers.IntegerField(min_value=0)


class TaskCloseSerializer(serializers.Serializer):
    completion_note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    evidence_url = serializers.CharField(required=False, allow_null=True)


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

    def get_board(self, payload: BoardPayload) -> dict[str, int | str]:
        board = payload["board"]
        return {"id": board.id, "name": board.name}

    def get_week(self, payload: BoardPayload) -> dict[str, int]:
        week = payload["week"]
        return {"iso_year": week.iso_year, "iso_week": week.iso_week}

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
                    "tasks": TaskBoardSerializer(tasks, many=True).data,
                },
            )
        return result
