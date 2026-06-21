from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.exceptions import JobCancelError, JobRetryError
from apps.jobs.models import BackgroundJob
from apps.jobs.selectors import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    list_jobs,
    parse_datetime_param,
    parse_int_param,
)
from apps.jobs.serializers import BackgroundJobSerializer
from apps.jobs.services import JobRetryService, JobService


class JobListView(APIView):
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
        jobs, count = list_jobs(
            job_type=request.query_params.get("job_type") or None,
            status=request.query_params.get("status") or None,
            created_from=parse_datetime_param(request.query_params.get("created_from")),
            created_to=parse_datetime_param(request.query_params.get("created_to")),
            page=page,
            page_size=page_size,
        )
        return Response(
            {
                "count": count,
                "page": page,
                "page_size": page_size,
                "results": BackgroundJobSerializer(jobs, many=True).data,
            },
        )


class JobDetailView(APIView):
    def get(self, request, pk: int):
        job = get_object_or_404(BackgroundJob, pk=pk)
        return Response(BackgroundJobSerializer(job).data)


class JobRetryView(APIView):
    def post(self, request, pk: int):
        job = get_object_or_404(BackgroundJob, pk=pk)
        try:
            retried = JobRetryService.retry(job)
        except JobRetryError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(BackgroundJobSerializer(retried).data)


class JobCancelView(APIView):
    def post(self, request, pk: int):
        job = get_object_or_404(BackgroundJob, pk=pk)
        try:
            cancelled = JobService.cancel(job)
        except JobCancelError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(BackgroundJobSerializer(cancelled).data)
