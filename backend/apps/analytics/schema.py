from drf_spectacular.utils import OpenApiParameter, inline_serializer
from rest_framework import serializers

from apps.analytics.serializers import AnalyticsExportSerializer

ANALYTICS_FILTER_PARAMETERS = [
    OpenApiParameter(
        name="week",
        type=str,
        location=OpenApiParameter.QUERY,
        required=False,
        description="ISO week, e.g. `2026-W12`.",
    ),
    OpenApiParameter(
        name="from",
        type=str,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Period start (date `YYYY-MM-DD` or datetime).",
    ),
    OpenApiParameter(
        name="to",
        type=str,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Period end (date `YYYY-MM-DD` or datetime).",
    ),
    OpenApiParameter(
        name="tags",
        type=str,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Comma-separated tag slugs.",
    ),
    OpenApiParameter(
        name="source",
        type=str,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Task source filter (`ui`, `api`, `json_import`, …).",
    ),
]

AnalyticsExportPreviewResponseSerializer = inline_serializer(
    name="AnalyticsExportPreviewResponse",
    fields={
        "export_type": serializers.CharField(),
        "sheets": serializers.ListField(
            child=inline_serializer(
                name="AnalyticsExportPreviewSheet",
                fields={
                    "id": serializers.CharField(),
                    "rows": serializers.ListField(
                        child=serializers.ListField(
                            child=serializers.CharField(
                                allow_blank=True,
                                allow_null=True,
                            ),
                        ),
                    ),
                    "total": serializers.IntegerField(),
                },
            ),
        ),
    },
)

AnalyticsExportListResponseSerializer = inline_serializer(
    name="AnalyticsExportListResponse",
    fields={
        "count": serializers.IntegerField(),
        "page": serializers.IntegerField(),
        "page_size": serializers.IntegerField(),
        "results": AnalyticsExportSerializer(many=True),
    },
)
