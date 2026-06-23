from rest_framework import serializers

from apps.analytics.models import AnalyticsExportJob, ExportType, FileFormat


class AnalyticsExportCreateSerializer(serializers.Serializer):
    export_type = serializers.ChoiceField(choices=ExportType.choices)
    file_format = serializers.ChoiceField(choices=FileFormat.choices)
    filters = serializers.DictField(required=False, default=dict)


class AnalyticsExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsExportJob
        fields = (
            "id",
            "export_type",
            "file_format",
            "status",
            "filters",
            "file_path",
            "file_size_bytes",
            "rows_count",
            "error_message",
            "expires_at",
            "created_at",
            "started_at",
            "finished_at",
            "background_job_id",
        )
        read_only_fields = fields
