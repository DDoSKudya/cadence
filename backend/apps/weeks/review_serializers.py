from rest_framework import serializers

from apps.tasks.models import Task
from apps.weeks.models import Week


class WeekOpenTaskSerializer(serializers.ModelSerializer):
    column_name = serializers.CharField(source="column.name", read_only=True)

    class Meta:
        model = Task
        fields = ("id", "title", "column_name")


class WeekReviewNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Week
        fields = ("review_notes",)


class WeekCloseSerializer(serializers.Serializer):
    carry_over = serializers.BooleanField(required=False, default=True)
