from rest_framework import serializers

from apps.notifications.models import NotificationJob


class NotificationJobSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source="task.title", read_only=True)

    class Meta:
        model = NotificationJob
        fields = (
            "id",
            "task_id",
            "task_title",
            "background_job_id",
            "telegram_chat_id",
            "message_text",
            "message_id",
            "status",
            "reason",
            "scheduled_at",
            "sent_at",
            "failed_at",
            "last_error",
            "dedup_key",
            "created_at",
        )
