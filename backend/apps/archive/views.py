from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.archive.selectors import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    archived_tasks_queryset,
    list_archived_tasks,
)
from apps.archive.serializers import (
    ArchiveTaskDetailSerializer,
    ArchiveTaskListSerializer,
)
from apps.jobs.selectors import parse_datetime_param, parse_int_param


class ArchiveTaskListView(APIView):
    def get(self, request):
        page = parse_int_param(
            request.query_params.get("page"),
            1,
            minimum=1,
            maximum=10_000,
        )
        page_size = parse_int_param(
            request.query_params.get("page_size"),
            DEFAULT_PAGE_SIZE,
            minimum=1,
            maximum=MAX_PAGE_SIZE,
        )
        tasks, count = list_archived_tasks(
            week=request.query_params.get("week") or None,
            tag=request.query_params.get("tag") or None,
            source=request.query_params.get("source") or None,
            closed_from=parse_datetime_param(request.query_params.get("closed_from")),
            closed_to=parse_datetime_param(request.query_params.get("closed_to")),
            search=request.query_params.get("search") or None,
            page=page,
            page_size=page_size,
        )
        return Response(
            {
                "count": count,
                "page": page,
                "page_size": page_size,
                "results": ArchiveTaskListSerializer(tasks, many=True).data,
            },
        )


class ArchiveTaskDetailView(APIView):
    def get(self, request, pk: int):
        task = get_object_or_404(archived_tasks_queryset(), pk=pk)
        return Response(ArchiveTaskDetailSerializer(task).data)
