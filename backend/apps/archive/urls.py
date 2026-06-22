from django.urls import path

from apps.archive.views import ArchiveTaskDetailView, ArchiveTaskListView

urlpatterns = [
    path("archive/tasks/", ArchiveTaskListView.as_view(), name="archive-task-list"),
    path(
        "archive/tasks/<int:pk>/",
        ArchiveTaskDetailView.as_view(),
        name="archive-task-detail",
    ),
]
