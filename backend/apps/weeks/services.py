import re
from datetime import date
from typing import TypedDict

from django.utils import timezone
from rest_framework.exceptions import ValidationError

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
