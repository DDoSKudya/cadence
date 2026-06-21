from django.urls import path

from apps.imports.views import (
    ImportDetailView,
    ImportListView,
    ImportRetryView,
    ImportScanView,
)

urlpatterns = [
    path("imports/", ImportListView.as_view(), name="import-list"),
    path("imports/scan/", ImportScanView.as_view(), name="import-scan"),
    path("imports/<int:pk>/", ImportDetailView.as_view(), name="import-detail"),
    path("imports/<int:pk>/retry/", ImportRetryView.as_view(), name="import-retry"),
]
