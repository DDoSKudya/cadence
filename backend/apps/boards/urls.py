from django.urls import path

from apps.boards.views import ColumnDetailView, ColumnListCreateView, ColumnReorderView

urlpatterns = [
    path("columns/", ColumnListCreateView.as_view(), name="column-list"),
    path("columns/reorder/", ColumnReorderView.as_view(), name="column-reorder"),
    path("columns/<int:pk>/", ColumnDetailView.as_view(), name="column-detail"),
]
