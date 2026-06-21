from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.boards.models import BoardColumn
from apps.boards.serializers import (
    BoardColumnCreateSerializer,
    BoardColumnReorderSerializer,
    BoardColumnSerializer,
    BoardColumnUpdateSerializer,
)
from apps.boards.services import ColumnSettingsService


class ColumnListCreateView(APIView):
    def get(self, request):
        board = ColumnSettingsService.get_default_board()
        columns = ColumnSettingsService.active_columns(board)
        serializer = BoardColumnSerializer(columns, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BoardColumnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = ColumnSettingsService.get_default_board()
        column = ColumnSettingsService.create_column(
            board,
            name=serializer.validated_data["name"],
            color=serializer.validated_data.get("color", "slate"),
            wip_limit=serializer.validated_data.get("wip_limit"),
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
        )
        return Response(BoardColumnSerializer(column).data)

    def delete(self, request, pk: int):
        column = self.get_object(pk)
        try:
            ColumnSettingsService.deactivate(column)
        except ValidationError as exc:
            if exc.get_codes() == "column_has_tasks":
                return Response({"detail": exc.detail}, status=status.HTTP_409_CONFLICT)
            raise
        return Response(status=status.HTTP_204_NO_CONTENT)


class ColumnReorderView(APIView):
    def post(self, request):
        serializer = BoardColumnReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = ColumnSettingsService.get_default_board()
        columns = ColumnSettingsService.reorder(
            board,
            serializer.validated_data["column_ids"],
        )
        return Response(BoardColumnSerializer(columns, many=True).data)
