from django.contrib.auth import login, logout
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.platform_status import collect_platform_status
from apps.common.service_logs import SERVICE_IDS, get_service_logs, log_file_exists
from apps.core.models import ProjectSettings
from apps.core.serializers import (
    LoginSerializer,
    ProjectSettingsSerializer,
    TagSerializer,
    TelegramBotCheckSerializer,
    UserSerializer,
)
from apps.core.tag_services import TagService
from apps.core.telegram_check import run_telegram_bot_check


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response({"user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProjectSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = ProjectSettingsSerializer

    def get_object(self):
        return ProjectSettings.load()


class TelegramBotCheckView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = TelegramBotCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settings_obj = ProjectSettings.load()
        token = serializer.validated_data.get("telegram_bot_token")
        result = run_telegram_bot_check(settings_obj, token=token)
        return Response(
            {
                "ok": result.ok,
                "message": result.message,
                "checked_at": result.checked_at,
                "bot_username": result.bot_username,
            },
        )


class PlatformStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        settings_obj = ProjectSettings.load()
        status = collect_platform_status(project_timezone=settings_obj.timezone)
        return Response(status.as_response())


class PlatformServiceLogsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, service_id: str):
        if service_id not in SERVICE_IDS:
            return Response(
                {"detail": "Unknown service."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            limit = int(request.query_params.get("limit", 200))
        except (TypeError, ValueError):
            limit = 200

        entries = get_service_logs(service_id, limit=limit)
        return Response(
            {
                "service_id": service_id,
                "entries": entries,
                "has_file": log_file_exists(service_id),
            },
        )


class TagListCreateView(generics.ListCreateAPIView):
    serializer_class = TagSerializer

    def get_queryset(self):
        return TagService.queryset_for_active_scheme()

    def perform_create(self, serializer):
        serializer.save(scheme=TagService.get_active_scheme())


class TagDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TagSerializer

    def get_queryset(self):
        return TagService.queryset_for_active_scheme()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
