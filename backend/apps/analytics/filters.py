from dataclasses import dataclass, field
from datetime import datetime, time

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.request import Request

from apps.core.models import Tag
from apps.core.tag_services import TagService
from apps.jobs.selectors import parse_datetime_param
from apps.weeks.models import Week
from apps.weeks.services import WeekService


@dataclass
class AnalyticsFilters:
    week: Week | None = None
    from_dt: datetime | None = None
    to_dt: datetime | None = None
    tags: list[str] = field(default_factory=list)
    source: str | None = None


def parse_filters(request: Request) -> AnalyticsFilters:
    week_value = request.query_params.get("week") or None
    week = WeekService.resolve_week(week_value) if week_value else None

    from_param = request.query_params.get("from")
    to_param = request.query_params.get("to")
    from_dt = _parse_date_start(from_param) or parse_datetime_param(from_param)
    to_dt = _parse_date_end(to_param) or parse_datetime_param(to_param)

    tags = _parse_tags(request)
    source = request.query_params.get("source") or None
    if source == "":
        source = None

    return AnalyticsFilters(
        week=week,
        from_dt=from_dt,
        to_dt=to_dt,
        tags=tags,
        source=source,
    )


def parse_filters_payload(payload: dict | None) -> AnalyticsFilters:
    data = payload or {}
    week_value = data.get("week")
    week = None
    if isinstance(week_value, str) and week_value.strip():
        week = WeekService.resolve_week(week_value.strip())

    from_value = data.get("from")
    to_value = data.get("to")
    from_dt = None
    to_dt = None
    if isinstance(from_value, str):
        from_dt = _parse_date_start(from_value) or parse_datetime_param(from_value)
    if isinstance(to_value, str):
        to_dt = _parse_date_end(to_value) or parse_datetime_param(to_value)

    tags = data.get("tags")
    parsed_tags: list[str] = []
    if isinstance(tags, list):
        parsed_tags = [str(item).strip() for item in tags if str(item).strip()]

    source = data.get("source")
    source_value = str(source).strip() if source else None
    if source_value == "":
        source_value = None

    return AnalyticsFilters(
        week=week,
        from_dt=from_dt,
        to_dt=to_dt,
        tags=parsed_tags,
        source=source_value,
    )


def period_bounds(filters: AnalyticsFilters) -> tuple[datetime | None, datetime | None]:
    if filters.week is not None:
        starts = timezone.make_aware(datetime.combine(filters.week.starts_on, time.min))
        ends = timezone.make_aware(datetime.combine(filters.week.ends_on, time.max))
        return starts, ends
    return filters.from_dt, filters.to_dt


def period_label(filters: AnalyticsFilters) -> dict:
    if filters.week is not None:
        return {
            "week": f"{filters.week.iso_year}-W{filters.week.iso_week:02d}",
        }
    label: dict[str, str] = {}
    if filters.from_dt is not None:
        label["from"] = filters.from_dt.date().isoformat()
    if filters.to_dt is not None:
        label["to"] = filters.to_dt.date().isoformat()
    return label


def _parse_tags(request: Request) -> list[str]:
    values = request.query_params.getlist("tag")
    if not values:
        raw = request.query_params.get("tags")
        if raw:
            values = [part.strip() for part in raw.split(",") if part.strip()]
    return [value.strip() for value in values if value.strip()]


def _parse_date_start(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = parse_date(value)
    if parsed is None:
        return None
    return timezone.make_aware(datetime.combine(parsed, time.min))


def _parse_date_end(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = parse_date(value)
    if parsed is None:
        return None
    return timezone.make_aware(datetime.combine(parsed, time.max))


def resolve_tag_ids(tags: list[str]) -> list[int]:
    if not tags:
        return []
    scheme = TagService.get_active_scheme()
    tag_ids: list[int] = []
    for value in tags:
        tag = Tag.objects.filter(scheme=scheme, slug=value).first()
        if tag is None:
            tag = Tag.objects.filter(scheme=scheme, name__iexact=value).first()
        if tag is not None:
            tag_ids.append(tag.id)
    return tag_ids
