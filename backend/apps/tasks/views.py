from typing import cast

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.boards.models import BoardColumn
from apps.boards.services import ColumnSettingsService
from apps.tasks.models import Task, TaskEvent
from apps.tasks.selectors import (
    active_tasks_for_board,
    build_board_payload,
    search_active_tasks,
)
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
    TaskUpdateService,
    create_task_from_request,
)
from apps.tasks.task_update_payload import build_task_update_input
from apps.weeks.rollover import WeekRolloverService
from apps.weeks.services import WeekService


class TaskListCreateView(APIView):
    def get(self, request: Request):
        board = ColumnSettingsService.get_default_board()
        week_value = request.query_params.get("week")
        week = WeekService.resolve_week(week_value)

        query = request.query_params.get("q", "")
        exclude_raw = request.query_params.get("exclude")
        exclude_task_id = int(exclude_raw) if exclude_raw else None
        if query.strip() or exclude_task_id is not None:
            tasks = search_active_tasks(
                board,
                query=query,
                exclude_task_id=exclude_task_id,
            )
            return Response(TaskSerializer(tasks, many=True).data)

        tasks = active_tasks_for_board(board, week)
        return Response(TaskSerializer(tasks, many=True).data)

    def post(self, request: Request):
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(TaskCreateData, serializer.validated_data)
        task = create_task_from_request(request, data)
        task = TaskDetailView._load_task(task.pk)
        return Response(
            TaskSerializer(task).data,
            status=status.HTTP_201_CREATED,
        )


class TaskDetailView(APIView):
    @staticmethod
    def _load_task(pk: int) -> Task:
        board = ColumnSettingsService.get_default_board()
        return get_object_or_404(
            Task.objects.select_related("week", "task_status").prefetch_related(
                "tags",
                "outgoing_links__to_task",
                "incoming_links__from_task",
            ),
            pk=pk,
            board=board,
        )

    def get_object(self, pk: int) -> Task:
        return self._load_task(pk)

    def get(self, request: Request, pk: int):
        task = self.get_object(pk)
        return Response(TaskSerializer(task).data)

    def patch(self, request: Request, pk: int):
        task = self.get_object(pk)
        serializer = TaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        update_input = build_task_update_input(request, data)
        task = TaskUpdateService.update(task, update_input)
        task = self._load_task(task.pk)
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
        WeekRolloverService.process()
        board = ColumnSettingsService.get_default_board()
        week_value = request.query_params.get("week")
        week = WeekService.resolve_week(week_value)
        payload = build_board_payload(board, week)
        return Response(BoardResponseSerializer(payload).data)
