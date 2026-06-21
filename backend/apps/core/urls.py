from django.urls import path

from apps.core.views import (
    LoginView,
    LogoutView,
    MeView,
    ProjectSettingsView,
    TagDetailView,
    TagListCreateView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("settings/", ProjectSettingsView.as_view(), name="settings"),
    path("tags/", TagListCreateView.as_view(), name="tag-list"),
    path("tags/<int:pk>/", TagDetailView.as_view(), name="tag-detail"),
]
