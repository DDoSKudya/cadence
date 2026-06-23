from django.urls import path

from apps.core.views import (
    LoginView,
    LogoutView,
    MeView,
    PlatformServiceLogsView,
    PlatformStatusView,
    ProjectSettingsView,
    TagDetailView,
    TagListCreateView,
    TelegramBotCheckView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("settings/", ProjectSettingsView.as_view(), name="settings"),
    path("platform/status/", PlatformStatusView.as_view(), name="platform-status"),
    path(
        "platform/services/<str:service_id>/logs/",
        PlatformServiceLogsView.as_view(),
        name="platform-service-logs",
    ),
    path(
        "settings/telegram/check/",
        TelegramBotCheckView.as_view(),
        name="settings-telegram-check",
    ),
    path("tags/", TagListCreateView.as_view(), name="tag-list"),
    path("tags/<int:pk>/", TagDetailView.as_view(), name="tag-detail"),
]
