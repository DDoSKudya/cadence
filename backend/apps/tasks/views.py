from typing import cast

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.boards.models import BoardColumn
from apps.boards.services import ColumnSettingsService
from apps.tasks.models import Task, TaskEvent
from apps.tasks.selectors import build_board_payload
from apps.tasks.serializers import (
    BoardResponseSerializer,
    TaskCloseSerializer,
    TaskCreateSerializer,
    TaskEventSerializer,
    TaskMoveSerializer,
    TaskSerializer,
    TaskUpdateSerializer,
)
from apps.tasks.services import (
    TaskCloseService,
    TaskCreateData,
    TaskMoveService,
    TaskReopenService,
    TaskUpdateInput,
    TaskUpdateService,
    create_task_from_request,
)
from apps.weeks.services import WeekService


class TaskListCreateView(APIView):
    def get(self, request: Request):
        board = ColumnSettingsService.get_default_board()
        week_value = request.query_params.get("week")
        week = WeekService.resolve_week(week_value)

        tasks = (
            Task.objects.filter(board=board, archived_at__isnull=True)
            .filter(week=week)
            .select_related("week")
            .prefetch_related("tags")
            .order_by("column_id", "position")
        )
        return Response(TaskSerializer(tasks, many=True).data)

    def post(self, request: Request):
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(TaskCreateData, serializer.validated_data)
        task = create_task_from_request(request, data)
        return Response(
            TaskSerializer(task).data,
            status=status.HTTP_201_CREATED,
        )


class TaskDetailView(APIView):
    def get_object(self, pk: int) -> Task:
        board = ColumnSettingsService.get_default_board()
        return get_object_or_404(
            Task.objects.select_related("week").prefetch_related("tags"),
            pk=pk,
            board=board,
        )

    def get(self, request: Request, pk: int):
        task = self.get_object(pk)
        return Response(TaskSerializer(task).data)

    def patch(self, request: Request, pk: int):
        task = self.get_object(pk)
        serializer = TaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        week = None
        week_provided = False
        clear_week = False
        if "week" in data:
            week_provided = True
            if data["week"] is None:
                clear_week = True
            else:
                week = WeekService.resolve_week(data["week"])

        clear_due_at = "due_at" in data and data["due_at"] is None
        clear_reminder_interval = (
            "reminder_interval_minutes" in data
            and data["reminder_interval_minutes"] is None
        )

        update_input = TaskUpdateInput(
            request=request,
            title=data.get("title"),
            description=data.get("description"),
            priority=data.get("priority"),
            week=week,
            week_provided=week_provided,
            clear_week=clear_week,
            due_at=data.get("due_at"),
            clear_due_at=clear_due_at,
            evidence_url=data.get("evidence_url"),
            reminder_enabled=data.get("reminder_enabled"),
            reminder_interval_minutes=data.get("reminder_interval_minutes"),
            clear_reminder_interval=clear_reminder_interval,
            tag_slugs=data.get("tags"),
        )
        task = TaskUpdateService.update(task, update_input)
        return Response(TaskSerializer(task).data)


class TaskMoveView(APIView):
    def post(self, request: Request, pk: int):
        board = ColumnSettingsService.get_default_board()
        task = get_object_or_404(Task, pk=pk, board=board)
        serializer = TaskMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_column = get_object_or_404(
            BoardColumn,
            pk=serializer.validated_data["target_column_id"],
            board=board,
            is_active=True,
        )
        task = TaskMoveService.move(
            task,
            target_column=target_column,
            target_position=serializer.validated_data["target_position"],
            request=request,
        )
        return Response(TaskSerializer(task).data)


class TaskCloseView(APIView):
    def post(self, request: Request, pk: int):
        board = ColumnSettingsService.get_default_board()
        task = get_object_or_404(Task, pk=pk, board=board)
        serializer = TaskCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TaskCloseService.close(
            task,
            completion_note=serializer.validated_data.get("completion_note", ""),
            evidence_url=serializer.validated_data.get("evidence_url"),
            request=request,
        )
        return Response(TaskSerializer(task).data)


class TaskReopenView(APIView):
    def post(self, request: Request, pk: int):
        board = ColumnSettingsService.get_default_board()
        task = get_object_or_404(Task, pk=pk, board=board)
        task = TaskReopenService.reopen(task, request=request)
        return Response(TaskSerializer(task).data)


class TaskEventsView(APIView):
    def get(self, request: Request, pk: int):
        board = ColumnSettingsService.get_default_board()
        task = get_object_or_404(Task, pk=pk, board=board)
        events = TaskEvent.objects.filter(task=task).order_by("-created_at")
        return Response(TaskEventSerializer(events, many=True).data)


class BoardView(APIView):
    def get(self, request: Request):
        board = ColumnSettingsService.get_default_board()
        week_value = request.query_params.get("week")
        week = WeekService.resolve_week(week_value)
        payload = build_board_payload(board, week)
        return Response(BoardResponseSerializer(payload).data)
