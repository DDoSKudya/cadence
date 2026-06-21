from datetime import datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.jobs.models import BackgroundJob

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def list_jobs(
    *,
    job_type: str | None = None,
    status: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[BackgroundJob], int]:
    queryset = BackgroundJob.objects.all()

    if job_type:
        queryset = queryset.filter(job_type=job_type)
    if status:
        queryset = queryset.filter(status=status)
    if created_from:
        queryset = queryset.filter(created_at__gte=created_from)
    if created_to:
        queryset = queryset.filter(created_at__lte=created_to)

    total = queryset.count()
    offset = (page - 1) * page_size
    jobs = list(queryset[offset : offset + page_size])
    return jobs, total


def parse_datetime_param(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed)
    return parsed


def parse_int_param(
    value: str | None,
    default: int,
    *,
    minimum: int = 1,
    maximum: int,
) -> int:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(minimum, min(parsed, maximum))
