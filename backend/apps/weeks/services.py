import re
from datetime import date, timedelta
from typing import TypedDict

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.tasks.models import Task
from apps.weeks.models import Week

WEEK_PATTERN = re.compile(r"^(?P<year>\d{4})-W(?P<week>\d{2})$")
ISO_WEEK_MIN = 1
ISO_WEEK_MAX = 53


class WeekBounds(TypedDict):
    starts_on: date
    ends_on: date


class WeekService:
    @staticmethod
    def get_or_create_current_week() -> Week:
        today = timezone.localdate()
        iso = today.isocalendar()
        return WeekService.get_or_create_week(iso.year, iso.week)

    @staticmethod
    def get_or_create_week(iso_year: int, iso_week: int) -> Week:
        bounds = WeekService._week_bounds(iso_year, iso_week)
        week, _created = Week.objects.get_or_create(
            iso_year=iso_year,
            iso_week=iso_week,
            defaults=bounds,
        )
        return week

    @staticmethod
    def parse_week(value: str) -> tuple[int, int]:
        match = WEEK_PATTERN.match(value.strip())
        if match is None:
            raise ValidationError("Week must use ISO format YYYY-Www.")

        iso_year = int(match.group("year"))
        iso_week = int(match.group("week"))
        if iso_week < ISO_WEEK_MIN or iso_week > ISO_WEEK_MAX:
            raise ValidationError("ISO week must be between 1 and 53.")

        return iso_year, iso_week

    @staticmethod
    def resolve_week(value: str | None) -> Week:
        if value is None:
            return WeekService.get_or_create_current_week()

        iso_year, iso_week = WeekService.parse_week(value)
        return WeekService.get_or_create_week(iso_year, iso_week)

    @staticmethod
    def _week_bounds(iso_year: int, iso_week: int) -> WeekBounds:
        starts_on = date.fromisocalendar(iso_year, iso_week, 1)
        ends_on = date.fromisocalendar(iso_year, iso_week, 7)
        return {"starts_on": starts_on, "ends_on": ends_on}

    @staticmethod
    def next_week(week: Week) -> Week:
        next_start = week.ends_on + timedelta(days=1)
        iso = next_start.isocalendar()
        return WeekService.get_or_create_week(iso.year, iso.week)


class WeekReviewData(TypedDict):
    week: Week
    tasks_total: int
    tasks_closed: int
    tasks_open: int
    open_tasks: list[Task]


class WeekReviewService:
    @staticmethod
    def build(week: Week) -> WeekReviewData:
        tasks = list(
            Task.objects.filter(week=week)
            .select_related("column")
            .order_by("column_id", "position"),
        )
        open_tasks = [task for task in tasks if task.archived_at is None]
        return {
            "week": week,
            "tasks_total": len(tasks),
            "tasks_closed": len(tasks) - len(open_tasks),
            "tasks_open": len(open_tasks),
            "open_tasks": open_tasks,
        }


class WeekCloseService:
    @staticmethod
    @transaction.atomic
    def close(week: Week, *, carry_over: bool = True) -> dict[str, int]:
        if week.closed_at is not None:
            raise ValidationError("Week is already closed.")

        today = timezone.localdate()
        if week.starts_on > today:
            raise ValidationError("Cannot close a future week.")

        open_tasks = list(
            Task.objects.filter(week=week, archived_at__isnull=True).order_by("id"),
        )
        carried = 0

        if carry_over and open_tasks:
            next_week = WeekService.next_week(week)
            carried = Task.objects.filter(
                pk__in=[task.pk for task in open_tasks],
            ).update(week=next_week, updated_at=timezone.now())

        week.closed_at = timezone.now()
        week.save(update_fields=["closed_at", "updated_at"])

        return {
            "week_id": week.id,
            "carried_over": carried,
            "open_tasks_before_close": len(open_tasks),
        }
