from django.urls import path

from apps.tasks.views import (
    BoardView,
    TaskCloseView,
    TaskDetailView,
    TaskEventsView,
    TaskListCreateView,
    TaskMoveView,
    TaskReopenView,
)

urlpatterns = [
    path("board/", BoardView.as_view(), name="board"),
    path("tasks/", TaskListCreateView.as_view(), name="task-list"),
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("tasks/<int:pk>/move/", TaskMoveView.as_view(), name="task-move"),
    path("tasks/<int:pk>/close/", TaskCloseView.as_view(), name="task-close"),
    path("tasks/<int:pk>/reopen/", TaskReopenView.as_view(), name="task-reopen"),
    path("tasks/<int:pk>/events/", TaskEventsView.as_view(), name="task-events"),
]
