from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from apps.core.models import ProjectSettings, Tag
from apps.core.telegram_check import run_telegram_bot_check
from apps.notifications.scheduling import refresh_default_reminder_schedules

TELEGRAM_RECIPIENT_KINDS = {"user", "group"}


def normalize_telegram_recipients(value: list) -> list[dict[str, str]]:
    seen: set[str] = set()
    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise serializers.ValidationError("Invalid recipient format.")
        chat_id = str(item.get("chat_id", "")).strip()
        if not chat_id:
            raise serializers.ValidationError("chat_id is required.")
        if chat_id in seen:
            raise serializers.ValidationError(f"Duplicate chat_id: {chat_id}")
        kind = item.get("kind")
        if kind not in TELEGRAM_RECIPIENT_KINDS:
            raise serializers.ValidationError("kind must be user or group.")
        seen.add(chat_id)
        normalized.append(
            {
                "chat_id": chat_id,
                "label": str(item.get("label", "")).strip(),
                "kind": kind,
            },
        )
    return normalized


class ProjectSettingsSerializer(serializers.ModelSerializer):
    telegram_bot_token_set = serializers.SerializerMethodField(read_only=True)
    telegram_bot_token = serializers.CharField(
        max_length=255,
        write_only=True,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = ProjectSettings
        fields = (
            "timezone",
            "language",
            "json_inbox_enabled",
            "telegram_enabled",
            "telegram_bot_token_set",
            "telegram_bot_token",
            "telegram_bot_username",
            "telegram_recipients",
            "telegram_bot_check_ok",
            "telegram_bot_check_message",
            "telegram_bot_checked_at",
            "default_reminder_interval_minutes",
            "stale_in_progress_minutes",
            "stale_planned_minutes",
            "quiet_hours_start",
            "quiet_hours_end",
            "updated_at",
        )
        read_only_fields = (
            "telegram_bot_check_ok",
            "telegram_bot_check_message",
            "telegram_bot_checked_at",
            "updated_at",
        )

    def get_telegram_bot_token_set(self, obj: ProjectSettings) -> bool:
        return bool(obj.telegram_bot_token)

    def to_representation(self, instance: ProjectSettings) -> dict:
        data = super().to_representation(instance)
        recipients = data.get("telegram_recipients")
        if not isinstance(recipients, list):
            data["telegram_recipients"] = []
        data["telegram_bot_username"] = data.get("telegram_bot_username") or ""
        data["telegram_bot_token_set"] = bool(instance.telegram_bot_token)
        data["telegram_bot_check_message"] = (
            data.get("telegram_bot_check_message") or ""
        )
        return data

    def validate_telegram_recipients(self, value):
        return normalize_telegram_recipients(value)

    def update(self, instance: ProjectSettings, validated_data):
        token = validated_data.pop("telegram_bot_token", None)
        telegram_token_changed = False
        if token is not None and token.strip():
            instance.telegram_bot_token = token.strip()
            telegram_token_changed = True

        telegram_related_fields = {
            "telegram_enabled",
            "telegram_bot_username",
            "telegram_recipients",
        }
        telegram_settings_changed = telegram_token_changed or any(
            field in validated_data for field in telegram_related_fields
        )

        reminder_interval_changed = (
            "default_reminder_interval_minutes" in validated_data
            and validated_data["default_reminder_interval_minutes"]
            != instance.default_reminder_interval_minutes
        )

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()

        if reminder_interval_changed:
            refresh_default_reminder_schedules(instance)

        if instance.telegram_enabled and telegram_settings_changed:
            run_telegram_bot_check(instance)

        return instance


class TelegramBotCheckSerializer(serializers.Serializer):
    telegram_bot_token = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context["request"]
        user = authenticate(
            request,
            username=attrs["username"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid credentials.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "is_staff")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug", "color", "is_active", "created_at")
        read_only_fields = ("id", "created_at")
