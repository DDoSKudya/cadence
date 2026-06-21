from rest_framework import serializers

from apps.jobs.models import BackgroundJob


class BackgroundJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackgroundJob
        fields = (
            "id",
            "job_type",
            "status",
            "payload",
            "result",
            "attempts",
            "max_attempts",
            "scheduled_at",
            "started_at",
            "finished_at",
            "last_error",
            "celery_task_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
