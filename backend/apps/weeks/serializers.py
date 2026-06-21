from rest_framework import serializers

from apps.weeks.models import Week


class WeekSerializer(serializers.ModelSerializer):
    class Meta:
        model = Week
        fields = (
            "id",
            "iso_year",
            "iso_week",
            "starts_on",
            "ends_on",
            "review_notes",
            "closed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
