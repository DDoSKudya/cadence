from django.urls import path

from apps.analytics.views import (
    AnalyticsArchiveView,
    AnalyticsBreakdownView,
    AnalyticsCycleTimeView,
    AnalyticsExportDetailView,
    AnalyticsExportDownloadView,
    AnalyticsExportListCreateView,
    AnalyticsNotificationsView,
    AnalyticsSummaryView,
    AnalyticsTaskFlowView,
    AnalyticsWeeklyTrendView,
)

urlpatterns = [
    path(
        "analytics/summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"
    ),
    path(
        "analytics/weekly-trend/",
        AnalyticsWeeklyTrendView.as_view(),
        name="analytics-weekly-trend",
    ),
    path(
        "analytics/breakdown/",
        AnalyticsBreakdownView.as_view(),
        name="analytics-breakdown",
    ),
    path(
        "analytics/cycle-time/",
        AnalyticsCycleTimeView.as_view(),
        name="analytics-cycle-time",
    ),
    path(
        "analytics/notifications/",
        AnalyticsNotificationsView.as_view(),
        name="analytics-notifications",
    ),
    path(
        "analytics/task-flow/",
        AnalyticsTaskFlowView.as_view(),
        name="analytics-task-flow",
    ),
    path(
        "analytics/archive/", AnalyticsArchiveView.as_view(), name="analytics-archive"
    ),
    path(
        "analytics/exports/",
        AnalyticsExportListCreateView.as_view(),
        name="analytics-export-list",
    ),
    path(
        "analytics/exports/<int:pk>/",
        AnalyticsExportDetailView.as_view(),
        name="analytics-export-detail",
    ),
    path(
        "analytics/exports/<int:pk>/download/",
        AnalyticsExportDownloadView.as_view(),
        name="analytics-export-download",
    ),
]
