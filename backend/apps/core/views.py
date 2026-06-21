from django.contrib.auth import login, logout
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import ProjectSettings, Tag
from apps.core.serializers import (
    LoginSerializer,
    ProjectSettingsSerializer,
    TagSerializer,
    UserSerializer,
)


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


class TagListCreateView(generics.ListCreateAPIView):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.filter(is_active=True)


class TagDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.filter(is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
