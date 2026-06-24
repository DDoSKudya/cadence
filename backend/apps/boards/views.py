from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.boards.constants import board_limits_payload
from apps.boards.models import BoardColumn
from apps.boards.scheme_services import BoardSchemeService
from apps.boards.serializers import (
    BoardColumnCreateSerializer,
    BoardColumnReorderSerializer,
    BoardColumnSerializer,
    BoardColumnUpdateSerializer,
    BoardSchemeCreateSerializer,
    BoardSchemeDeleteSerializer,
    BoardSchemeSerializer,
    BoardSchemeSwitchSerializer,
    ColumnWorkflowSerializer,
    TaskStatusGraphSerializer,
    TaskStatusLayoutSerializer,
)
from apps.boards.services import (
    ColumnSettingsService,
    ColumnWorkflowService,
)
from apps.boards.task_status_services import TaskStatusService


def scheme_switch_payload(board) -> dict[str, object]:
    columns = ColumnSettingsService.active_columns(board)
    scheme = BoardSchemeService.get_active_scheme(board)
    return {
        "scheme": BoardSchemeSerializer(scheme).data if scheme else None,
        "columns": BoardColumnSerializer(columns, many=True).data,
        "workflow": ColumnWorkflowService.get_workflow(board),
        "status_graph": TaskStatusService.get_graph(board),
    }


class ColumnListCreateView(APIView):
    def get(self, request):
        board = ColumnSettingsService.get_default_board()
        columns = ColumnSettingsService.active_columns(board)
        scheme = BoardSchemeService.get_active_scheme(board)
        return Response(
            {
                "scheme": BoardSchemeSerializer(scheme).data if scheme else None,
                "columns": BoardColumnSerializer(columns, many=True).data,
                "limits": board_limits_payload(),
            },
        )

    def post(self, request):
        serializer = BoardColumnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = ColumnSettingsService.get_default_board()
        column = ColumnSettingsService.create_column(
            board,
            name=serializer.validated_data["name"],
            color=serializer.validated_data.get("color", "slate"),
            wip_limit=serializer.validated_data.get("wip_limit"),
            system_type=serializer.validated_data.get("system_type", "backlog"),
        )
        return Response(
            BoardColumnSerializer(column).data,
            status=status.HTTP_201_CREATED,
        )


class ColumnDetailView(APIView):
    def get_object(self, pk: int) -> BoardColumn:
        board = ColumnSettingsService.get_default_board()
        return get_object_or_404(BoardColumn, pk=pk, board=board, is_active=True)

    def patch(self, request, pk: int):
        column = self.get_object(pk)
        serializer = BoardColumnUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        column = ColumnSettingsService.update_column(
            column,
            name=data.get("name"),
            color=data.get("color"),
            wip_limit=data.get("wip_limit"),
            clear_wip_limit="wip_limit" in data and data["wip_limit"] is None,
            system_type=data.get("system_type"),
            task_status_ids=data.get("task_status_ids"),
        )
        return Response(BoardColumnSerializer(column).data)

    def delete(self, request, pk: int):
        column = self.get_object(pk)
        try:
            ColumnSettingsService.deactivate(column)
        except ValidationError as exc:
            codes = exc.get_codes()
            if codes in ("column_has_tasks", ["column_has_tasks"]):
                return Response({"detail": exc.detail}, status=status.HTTP_409_CONFLICT)
            if codes in (
                "column_locked",
                "scheme_locked",
                ["column_locked"],
                ["scheme_locked"],
            ):
                return Response(
                    {"detail": exc.detail}, status=status.HTTP_403_FORBIDDEN
                )
            raise
        return Response(status=status.HTTP_204_NO_CONTENT)


class ColumnReorderView(APIView):
    def post(self, request):
        serializer = BoardColumnReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = ColumnSettingsService.get_default_board()
        try:
            columns = ColumnSettingsService.reorder(
                board,
                serializer.validated_data["column_ids"],
            )
        except ValidationError as exc:
            return Response(
                {"detail": str(exc.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(BoardColumnSerializer(columns, many=True).data)


class ColumnWorkflowView(APIView):
    def get(self, request):
        board = ColumnSettingsService.get_default_board()
        return Response(ColumnWorkflowService.get_workflow(board))

    def put(self, request):
        serializer = ColumnWorkflowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = ColumnSettingsService.get_default_board()
        try:
            workflow = ColumnWorkflowService.set_transitions(
                board,
                serializer.validated_data["transitions"],
            )
        except ValidationError as exc:
            return Response(
                {"detail": str(exc.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(workflow)


class TaskStatusGraphView(APIView):
    def get(self, request):
        board = ColumnSettingsService.get_default_board()
        return Response(TaskStatusService.get_graph(board))

    def put(self, request):
        serializer = TaskStatusGraphSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = ColumnSettingsService.get_default_board()
        try:
            graph = TaskStatusService.save_graph(
                board,
                statuses=serializer.validated_data["statuses"],
                transitions=serializer.validated_data["transitions"],
            )
        except ValidationError as exc:
            return Response(
                {"detail": str(exc.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(graph)

    def patch(self, request):
        serializer = TaskStatusLayoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = ColumnSettingsService.get_default_board()
        try:
            graph = TaskStatusService.save_layout(
                board,
                statuses=serializer.validated_data["statuses"],
            )
        except ValidationError as exc:
            return Response(
                {"detail": str(exc.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(graph)


class BoardSchemeListView(APIView):
    def get(self, request):
        schemes = BoardSchemeService.list_schemes()
        return Response(
            {
                "schemes": BoardSchemeSerializer(schemes, many=True).data,
                "limits": board_limits_payload(),
            },
        )

    def post(self, request):
        serializer = BoardSchemeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        scheme = BoardSchemeService.create_custom_scheme(
            name=data["name"],
            description=data.get("description", ""),
        )

        if not data.get("switch", True):
            return Response(
                BoardSchemeSerializer(scheme).data,
                status=status.HTTP_201_CREATED,
            )

        if not data.get("confirm", False):
            raise ValidationError("Scheme switch must be confirmed.")

        board = ColumnSettingsService.get_default_board()
        try:
            BoardSchemeService.switch_scheme(board, scheme.slug)
        except ValidationError as exc:
            return Response(
                {"detail": str(exc.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            scheme_switch_payload(board),
            status=status.HTTP_201_CREATED,
        )


class BoardSchemeSwitchView(APIView):
    def post(self, request):
        serializer = BoardSchemeSwitchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["confirm"]:
            raise ValidationError("Scheme switch must be confirmed.")

        board = ColumnSettingsService.get_default_board()
        try:
            BoardSchemeService.switch_scheme(
                board,
                serializer.validated_data["slug"],
            )
        except ValidationError as exc:
            return Response(
                {"detail": str(exc.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(scheme_switch_payload(board))


class BoardSchemeDetailView(APIView):
    def delete(self, request, slug: str):
        serializer = BoardSchemeDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["confirm"]:
            raise ValidationError("Scheme deletion must be confirmed.")

        board = ColumnSettingsService.get_default_board()
        try:
            BoardSchemeService.delete_scheme(board, slug)
        except ValidationError as exc:
            codes = exc.get_codes()
            if codes in ("scheme_locked", ["scheme_locked"]):
                return Response(
                    {"detail": exc.detail}, status=status.HTTP_403_FORBIDDEN
                )
            return Response(
                {"detail": str(exc.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
