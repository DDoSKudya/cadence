from rest_framework import serializers

from apps.boards.models import BoardColumn


class BoardColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardColumn
        fields = (
            "id",
            "name",
            "system_type",
            "color",
            "position",
            "is_active",
            "wip_limit",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "system_type",
            "position",
            "is_active",
            "created_at",
            "updated_at",
        )


class BoardColumnCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    color = serializers.CharField(max_length=20, required=False, default="slate")
    wip_limit = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class BoardColumnUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    color = serializers.CharField(max_length=20, required=False)
    wip_limit = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class BoardColumnReorderSerializer(serializers.Serializer):
    column_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
