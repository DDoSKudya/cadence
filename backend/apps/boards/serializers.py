from rest_framework import serializers

from apps.boards.models import BoardColumn, BoardScheme, SystemType, TaskStatus


class BoardColumnSerializer(serializers.ModelSerializer):
    bound_status_ids = serializers.SerializerMethodField()

    class Meta:
        model = BoardColumn
        fields = (
            "id",
            "name",
            "system_type",
            "color",
            "position",
            "is_active",
            "is_locked",
            "wip_limit",
            "bound_status_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "position",
            "is_active",
            "is_locked",
            "bound_status_ids",
            "created_at",
            "updated_at",
        )

    def get_bound_status_ids(self, obj: BoardColumn) -> list[int]:
        prefetched = getattr(obj, "_prefetched_bound_status_ids", None)
        if prefetched is not None:
            return prefetched
        return list(
            TaskStatus.objects.filter(column_id=obj.id).values_list("id", flat=True),
        )


class BoardColumnCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    color = serializers.CharField(max_length=20, required=False, default="slate")
    wip_limit = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    system_type = serializers.ChoiceField(
        choices=SystemType.choices,
        required=False,
        default=SystemType.BACKLOG,
    )


class BoardColumnUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    color = serializers.CharField(max_length=20, required=False)
    wip_limit = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    system_type = serializers.ChoiceField(choices=SystemType.choices, required=False)
    task_status_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )


class BoardColumnReorderSerializer(serializers.Serializer):
    column_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )


class ColumnTransitionItemSerializer(serializers.Serializer):
    from_column_id = serializers.IntegerField(min_value=1)
    to_column_id = serializers.IntegerField(min_value=1)


class ColumnWorkflowSerializer(serializers.Serializer):
    transitions = ColumnTransitionItemSerializer(many=True)


class TaskStatusSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    client_key = serializers.CharField(required=False, allow_blank=True, default="")
    name = serializers.CharField(max_length=100)
    color = serializers.CharField(max_length=20, required=False, default="slate")
    layout_x = serializers.FloatField(required=False, default=0)
    layout_y = serializers.FloatField(required=False, default=0)
    is_initial = serializers.BooleanField(required=False, default=False)
    is_terminal = serializers.BooleanField(required=False, default=False)
    column_id = serializers.IntegerField(required=False, allow_null=True)
    rules = serializers.DictField(required=False, default=dict)


class TaskStatusTransitionItemSerializer(serializers.Serializer):
    from_status_id = serializers.CharField()
    to_status_id = serializers.CharField()
    rules = serializers.DictField(required=False, default=dict)


class TaskStatusGraphSerializer(serializers.Serializer):
    statuses = TaskStatusSerializer(many=True)
    transitions = TaskStatusTransitionItemSerializer(many=True)


class TaskStatusLayoutItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    layout_x = serializers.FloatField()
    layout_y = serializers.FloatField()


class TaskStatusLayoutSerializer(serializers.Serializer):
    statuses = TaskStatusLayoutItemSerializer(many=True)


class BoardSchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardScheme
        fields = (
            "slug",
            "name",
            "description",
            "is_locked",
        )


class BoardSchemeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    switch = serializers.BooleanField(required=False, default=True)
    confirm = serializers.BooleanField(required=False, default=False)


class BoardSchemeSwitchSerializer(serializers.Serializer):
    slug = serializers.SlugField(max_length=50)
    confirm = serializers.BooleanField()


class BoardSchemeDeleteSerializer(serializers.Serializer):
    confirm = serializers.BooleanField()
