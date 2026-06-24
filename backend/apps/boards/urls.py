from django.urls import path

from apps.boards.views import (
    BoardSchemeDetailView,
    BoardSchemeListView,
    BoardSchemeSwitchView,
    ColumnDetailView,
    ColumnListCreateView,
    ColumnReorderView,
    ColumnWorkflowView,
    TaskStatusGraphView,
)

urlpatterns = [
    path("board/schemes/", BoardSchemeListView.as_view(), name="board-scheme-list"),
    path(
        "board/schemes/switch/",
        BoardSchemeSwitchView.as_view(),
        name="board-scheme-switch",
    ),
    path(
        "board/schemes/<slug:slug>/",
        BoardSchemeDetailView.as_view(),
        name="board-scheme-detail",
    ),
    path("columns/", ColumnListCreateView.as_view(), name="column-list"),
    path("columns/reorder/", ColumnReorderView.as_view(), name="column-reorder"),
    path("columns/workflow/", ColumnWorkflowView.as_view(), name="column-workflow"),
    path("task-statuses/", TaskStatusGraphView.as_view(), name="task-status-graph"),
    path("columns/<int:pk>/", ColumnDetailView.as_view(), name="column-detail"),
]
