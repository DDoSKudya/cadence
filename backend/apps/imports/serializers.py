from rest_framework import serializers

from apps.imports.models import ImportLog


class ImportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportLog
        fields = (
            "id",
            "filename",
            "original_path",
            "checksum",
            "idempotency_key",
            "schema_version",
            "source_label",
            "status",
            "tasks_created",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
        )
        read_only_fields = fields
