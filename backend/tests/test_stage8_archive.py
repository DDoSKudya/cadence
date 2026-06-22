import pytest
from django.urls import reverse
from django.utils import timezone

from apps.boards.models import BoardColumn, SystemType
from apps.boards.services import ColumnSettingsService
from apps.core.models import ApiKey
from apps.tasks.models import Task
from apps.weeks.services import WeekService


@pytest.fixture
def api_client_auth(client):
    api_key, raw_key = ApiKey.issue("archive-tests")
    client.defaults["HTTP_AUTHORIZATION"] = f"Api-Key {raw_key}"
    return client, api_key


@pytest.fixture
def planned_column():
    board = ColumnSettingsService.get_default_board()
    return BoardColumn.objects.get(board=board, system_type=SystemType.PLANNED)


@pytest.fixture
def current_week():
    return WeekService.get_or_create_current_week()


def create_task(client, *, title: str, column_id: int, week: str | None = None):
    payload = {"title": title, "column_id": column_id}
    if week is not None:
        payload["week"] = week
    return client.post(
        reverse("task-list"),
        payload,
        content_type="application/json",
    )


def close_task(client, task_id: int):
    return client.post(
        reverse("task-close", args=[task_id]),
        {"completion_note": "Done"},
        content_type="application/json",
    )


@pytest.mark.django_db
def test_archive_lists_closed_tasks_only(api_client_auth, planned_column, current_week):
    client, _api_key = api_client_auth
    week_key = f"{current_week.iso_year}-W{current_week.iso_week:02d}"

    open_response = create_task(
        client,
        title="Still open",
        column_id=planned_column.id,
        week=week_key,
    )
    closed_response = create_task(
        client,
        title="Archived task",
        column_id=planned_column.id,
        week=week_key,
    )
    close_task(client, closed_response.json()["id"])

    response = client.get(reverse("archive-task-list"))

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Archived task"
    assert open_response.json()["id"] not in {item["id"] for item in data["results"]}


@pytest.mark.django_db
def test_archive_detail_includes_events(api_client_auth, planned_column):
    client, _api_key = api_client_auth
    task_id = create_task(
        client,
        title="With history",
        column_id=planned_column.id,
    ).json()["id"]
    close_task(client, task_id)

    response = client.get(reverse("archive-task-detail", args=[task_id]))

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "With history"
    assert len(data["events"]) >= 2
    assert any(event["event_type"] == "closed" for event in data["events"])


@pytest.mark.django_db
def test_archive_rejects_active_task(api_client_auth, planned_column):
    client, _api_key = api_client_auth
    task_id = create_task(
        client,
        title="Active",
        column_id=planned_column.id,
    ).json()["id"]

    response = client.get(reverse("archive-task-detail", args=[task_id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_week_review_get_and_patch(api_client_auth, planned_column, current_week):
    client, _api_key = api_client_auth
    week_key = f"{current_week.iso_year}-W{current_week.iso_week:02d}"
    create_task(client, title="Open one", column_id=planned_column.id, week=week_key)
    closed = create_task(
        client,
        title="Closed one",
        column_id=planned_column.id,
        week=week_key,
    )
    close_task(client, closed.json()["id"])

    response = client.get(reverse("week-review", args=[current_week.id]))

    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["tasks_total"] == 2
    assert data["stats"]["tasks_closed"] == 1
    assert data["stats"]["tasks_open"] == 1
    assert len(data["open_tasks"]) == 1

    patch_response = client.patch(
        reverse("week-review", args=[current_week.id]),
        {"review_notes": "Good week"},
        content_type="application/json",
    )

    assert patch_response.status_code == 200
    current_week.refresh_from_db()
    assert current_week.review_notes == "Good week"


@pytest.mark.django_db
def test_week_close_carries_over_open_tasks(
    api_client_auth,
    planned_column,
    current_week,
):
    client, _api_key = api_client_auth
    week_key = f"{current_week.iso_year}-W{current_week.iso_week:02d}"
    open_task_id = create_task(
        client,
        title="Carry me",
        column_id=planned_column.id,
        week=week_key,
    ).json()["id"]

    response = client.post(
        reverse("week-close", args=[current_week.id]),
        {"carry_over": True},
        content_type="application/json",
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["carried_over"] == 1

    next_week = WeekService.next_week(current_week)
    task = Task.objects.get(pk=open_task_id)
    assert task.week_id == next_week.id
    current_week.refresh_from_db()
    assert current_week.closed_at is not None


@pytest.mark.django_db
def test_week_close_is_idempotent(api_client_auth, current_week):
    client, _api_key = api_client_auth
    current_week.closed_at = timezone.now()
    current_week.save(update_fields=["closed_at", "updated_at"])

    response = client.post(
        reverse("week-close", args=[current_week.id]),
        content_type="application/json",
    )

    assert response.status_code == 400
