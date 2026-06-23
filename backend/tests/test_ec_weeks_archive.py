from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import Tag
from apps.tasks.models import Task
from apps.weeks.services import WeekService
from conftest import close_task_via_api, create_task_via_api


@pytest.mark.parametrize(
    ("value", "is_valid"),
    [
        pytest.param("2026-W01", True, id="ec_parse_week_iso_valid"),
        pytest.param("2026-W53", True, id="ec_parse_week_upper_boundary_valid"),
        pytest.param("2026-W00", False, id="ec_parse_week_lower_boundary_invalid"),
        pytest.param("2026/01", False, id="ec_parse_week_wrong_format_invalid"),
    ],
)
def test_weeks_ec_parse_week_validity_classes(value, is_valid):
    if is_valid:
        year, week = WeekService.parse_week(value)
        assert year == 2026
        assert 1 <= week <= 53
    else:
        with pytest.raises(ValidationError):
            WeekService.parse_week(value)


@pytest.mark.django_db
def test_weeks_ec_current_week_endpoint_returns_active_week(api_client):
    response = api_client.get(reverse("week-current"))
    assert response.status_code == 200
    assert "iso_year" in response.json()
    assert "iso_week" in response.json()


@pytest.mark.django_db
def test_weeks_ec_week_list_returns_weeks(api_client, current_week):
    response = api_client.get(reverse("week-list"))
    assert response.status_code == 200
    assert any(item["id"] == current_week.id for item in response.json())


@pytest.mark.django_db
def test_weeks_ec_review_notes_patch_updates_week(api_client, current_week):
    response = api_client.patch(
        reverse("week-review", args=[current_week.id]),
        {"review_notes": "EC review notes"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["review_notes"] == "EC review notes"


@pytest.mark.django_db
def test_weeks_ec_close_open_week_with_carry_over_true_moves_open_tasks(
    api_client,
    planned_column,
    current_week,
    week_key,
):
    created = create_task_via_api(
        api_client,
        title="Carry me",
        column_id=planned_column.id,
        week=week_key,
    )
    task_id = created.json()["id"]
    response = api_client.post(
        reverse("week-close", args=[current_week.id]),
        {"carry_over": True},
        content_type="application/json",
    )
    assert response.status_code == 200
    task = Task.objects.get(pk=task_id)
    assert task.week_id != current_week.id


@pytest.mark.django_db
def test_weeks_ec_close_open_week_with_carry_over_false_keeps_open_tasks(
    api_client,
    planned_column,
    current_week,
    week_key,
):
    created = create_task_via_api(
        api_client,
        title="Stay week",
        column_id=planned_column.id,
        week=week_key,
    )
    task_id = created.json()["id"]
    response = api_client.post(
        reverse("week-close", args=[current_week.id]),
        {"carry_over": False},
        content_type="application/json",
    )
    assert response.status_code == 200
    task = Task.objects.get(pk=task_id)
    assert task.week_id == current_week.id


@pytest.mark.django_db
def test_weeks_ec_close_already_closed_week_rejected(api_client, current_week):
    first = api_client.post(
        reverse("week-close", args=[current_week.id]), content_type="application/json"
    )
    assert first.status_code == 200
    second = api_client.post(
        reverse("week-close", args=[current_week.id]), content_type="application/json"
    )
    assert second.status_code == 400


@pytest.mark.django_db
def test_weeks_ec_close_future_week_rejected(api_client):
    future = timezone.localdate() + timedelta(days=21)
    iso = future.isocalendar()
    future_week = WeekService.get_or_create_week(iso.year, iso.week)
    response = api_client.post(
        reverse("week-close", args=[future_week.id]), content_type="application/json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_archive_ec_list_filters_by_week_tag_search(
    api_client, planned_column, week_key
):
    Tag.objects.create(name="Focus", slug="focus")
    first = create_task_via_api(
        api_client,
        title="Archived focus task",
        column_id=planned_column.id,
        week=week_key,
        tags=["focus"],
    )
    second = create_task_via_api(
        api_client,
        title="Archived plain task",
        column_id=planned_column.id,
        week=week_key,
    )
    close_task_via_api(api_client, first.json()["id"])
    close_task_via_api(api_client, second.json()["id"])
    response = api_client.get(
        reverse("archive-task-list"),
        {"week": week_key, "tag": "focus", "search": "focus"},
    )
    assert response.status_code == 200
    assert response.json()["count"] >= 1
    assert any("focus" in item["title"].lower() for item in response.json()["results"])


@pytest.mark.django_db
def test_archive_ec_detail_for_active_task_returns_404(api_client, planned_column):
    created = create_task_via_api(
        api_client, title="Still active", column_id=planned_column.id
    )
    response = api_client.get(
        reverse("archive-task-detail", args=[created.json()["id"]])
    )
    assert response.status_code == 404
