from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics import selectors
from apps.analytics.constants import DEFAULT_WEEKS_COUNT, MAX_WEEKS_COUNT
from apps.analytics.filters import parse_filters, period_label
from apps.analytics.models import AnalyticsExportJob, ExportStatus
from apps.analytics.serializers import (
    AnalyticsExportCreateSerializer,
    AnalyticsExportSerializer,
)
from apps.analytics.services import AnalyticsExportService
from apps.jobs.selectors import parse_int_param


class AnalyticsSummaryView(APIView):
    def get(self, request):
        filters = parse_filters(request)
        data = selectors.get_summary(filters)
        data["period"] = period_label(filters)
        return Response(data)


class AnalyticsWeeklyTrendView(APIView):
    def get(self, request):
        filters = parse_filters(request)
        weeks = parse_int_param(
            request.query_params.get("weeks"),
            DEFAULT_WEEKS_COUNT,
            minimum=1,
            maximum=MAX_WEEKS_COUNT,
        )
        return Response(selectors.get_weekly_trend(filters, weeks_count=weeks))


class AnalyticsBreakdownView(APIView):
    def get(self, request):
        filters = parse_filters(request)
        group_by = request.query_params.get("group_by", "tag")
        return Response(selectors.get_breakdown(filters, group_by=group_by))


class AnalyticsCycleTimeView(APIView):
    def get(self, request):
        filters = parse_filters(request)
        return Response(selectors.get_cycle_time(filters))


class AnalyticsNotificationsView(APIView):
    def get(self, request):
        filters = parse_filters(request)
        return Response(selectors.get_notifications(filters))


class AnalyticsTaskFlowView(APIView):
    def get(self, request):
        filters = parse_filters(request)
        return Response(selectors.get_task_flow(filters))


class AnalyticsArchiveView(APIView):
    def get(self, request):
        filters = parse_filters(request)
        return Response(selectors.get_archive_analytics(filters))


class AnalyticsExportListCreateView(APIView):
    def get(self, request):
        page = parse_int_param(
            request.query_params.get("page"), 1, minimum=1, maximum=10_000
        )
        page_size = parse_int_param(
            request.query_params.get("page_size"),
            20,
            minimum=1,
            maximum=100,
        )
        queryset = AnalyticsExportJob.objects.all()
        total = queryset.count()
        offset = (page - 1) * page_size
        exports = queryset[offset : offset + page_size]
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": AnalyticsExportSerializer(exports, many=True).data,
            },
        )

    def post(self, request):
        serializer = AnalyticsExportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        filters = AnalyticsExportService.validate_filters_payload(
            serializer.validated_data.get("filters"),
        )
        export_job = AnalyticsExportService.create(
            export_type=serializer.validated_data["export_type"],
            file_format=serializer.validated_data["file_format"],
            filters=filters,
            requested_by=request.user if request.user.is_authenticated else None,
        )
        return Response(
            AnalyticsExportSerializer(export_job).data,
            status=status.HTTP_201_CREATED,
        )


class AnalyticsExportDetailView(APIView):
    def get(self, request, pk: int):
        export_job = get_object_or_404(AnalyticsExportJob, pk=pk)
        return Response(AnalyticsExportSerializer(export_job).data)


class AnalyticsExportDownloadView(APIView):
    def get(self, request, pk: int):
        export_job = get_object_or_404(AnalyticsExportJob, pk=pk)
        if export_job.status != ExportStatus.SUCCEEDED:
            return Response(
                {"detail": "Export is not ready for download."},
                status=status.HTTP_409_CONFLICT,
            )

        path = AnalyticsExportService.resolve_download_path(export_job)
        filename = path.name
        return FileResponse(path.open("rb"), as_attachment=True, filename=filename)
