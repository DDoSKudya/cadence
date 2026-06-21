import pytest
from django.urls import reverse

from apps.boards.models import BoardColumn, SystemType
from apps.boards.services import ColumnSettingsService
from apps.core.models import ApiKey
from apps.tasks.models import TaskEvent, TaskEventType
from apps.weeks.services import WeekService


@pytest.fixture
def api_client_auth(client):
    api_key, raw_key = ApiKey.issue("tests")
    client.defaults["HTTP_AUTHORIZATION"] = f"Api-Key {raw_key}"
    return client, api_key


@pytest.fixture
def backlog_column():
    board = ColumnSettingsService.get_default_board()
    return BoardColumn.objects.get(board=board, system_type=SystemType.BACKLOG)


@pytest.fixture
def planned_column():
    board = ColumnSettingsService.get_default_board()
    return BoardColumn.objects.get(board=board, system_type=SystemType.PLANNED)


@pytest.fixture
def done_column():
    board = ColumnSettingsService.get_default_board()
    return BoardColumn.objects.get(board=board, system_type=SystemType.DONE)


def create_task(client, *, title: str, column_id: int, week: str | None = None):
    payload = {"title": title, "column_id": column_id}
    if week is not None:
        payload["week"] = week
    return client.post(
        reverse("task-list"),
        payload,
        content_type="application/json",
    )


@pytest.mark.django_db
def test_create_task(api_client_auth, backlog_column):
    client, _api_key = api_client_auth
    week = WeekService.get_or_create_current_week()

    response = create_task(
        client,
        title="Разобрать RabbitMQ",
        column_id=backlog_column.id,
        week=f"{week.iso_year}-W{week.iso_week:02d}",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Разобрать RabbitMQ"
    assert data["column_id"] == backlog_column.id
    assert data["week"]["iso_year"] == week.iso_year
    assert TaskEvent.objects.filter(
        task_id=data["id"],
        event_type=TaskEventType.CREATED,
    ).exists()


@pytest.mark.django_db
def test_move_task_between_columns(api_client_auth, backlog_column, planned_column):
    client, _api_key = api_client_auth
    create_response = create_task(
        client,
        title="Move me",
        column_id=backlog_column.id,
    )
    task_id = create_response.json()["id"]

    response = client.post(
        reverse("task-move", args=[task_id]),
        {"target_column_id": planned_column.id, "target_position": 0},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["column_id"] == planned_column.id
    assert response.json()["position"] == 0
    assert TaskEvent.objects.filter(
        task_id=task_id,
        event_type=TaskEventType.MOVED,
    ).exists()


@pytest.mark.django_db
def test_close_task_archives_and_moves_to_done(
    api_client_auth,
    planned_column,
    done_column,
):
    client, _api_key = api_client_auth
    create_response = create_task(
        client,
        title="Close me",
        column_id=planned_column.id,
    )
    task_id = create_response.json()["id"]

    response = client.post(
        reverse("task-close", args=[task_id]),
        {
            "completion_note": "Done",
            "evidence_url": "https://example.com/pr/1",
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["column_id"] == done_column.id
    assert data["closed_at"] is not None
    assert data["archived_at"] is not None
    assert data["completion_note"] == "Done"
    assert TaskEvent.objects.filter(
        task_id=task_id,
        event_type=TaskEventType.CLOSED,
    ).exists()


@pytest.mark.django_db
def test_reopen_task_returns_to_planned(
    api_client_auth,
    planned_column,
    done_column,
):
    client, _api_key = api_client_auth
    create_response = create_task(
        client,
        title="Reopen me",
        column_id=planned_column.id,
    )
    task_id = create_response.json()["id"]
    client.post(reverse("task-close", args=[task_id]), content_type="application/json")

    response = client.post(
        reverse("task-reopen", args=[task_id]),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["column_id"] == planned_column.id
    assert data["closed_at"] is None
    assert data["archived_at"] is None
    assert TaskEvent.objects.filter(
        task_id=task_id,
        event_type=TaskEventType.REOPENED,
    ).exists()


@pytest.mark.django_db
def test_board_groups_tasks_by_columns(api_client_auth, backlog_column, planned_column):
    client, _api_key = api_client_auth
    create_task(client, title="Backlog task", column_id=backlog_column.id)
    create_task(client, title="Planned task", column_id=planned_column.id)

    response = client.get(reverse("board"))

    assert response.status_code == 200
    data = response.json()
    assert data["board"]["name"] == "Main"
    assert len(data["columns"]) == 4

    backlog = next(item for item in data["columns"] if item["system_type"] == "backlog")
    planned = next(item for item in data["columns"] if item["system_type"] == "planned")
    assert len(backlog["tasks"]) == 1
    assert backlog["tasks"][0]["title"] == "Backlog task"
    assert len(planned["tasks"]) == 1
    assert planned["tasks"][0]["title"] == "Planned task"


@pytest.mark.django_db
def test_board_includes_weekless_tasks_for_selected_week(
    api_client_auth,
    backlog_column,
):
    client, _api_key = api_client_auth
    week = WeekService.get_or_create_current_week()
    create_task(client, title="Weekless", column_id=backlog_column.id)
    create_task(
        client,
        title="Week task",
        column_id=backlog_column.id,
        week=f"{week.iso_year}-W{week.iso_week:02d}",
    )

    response = client.get(
        reverse("board"),
        {"week": f"{week.iso_year}-W{week.iso_week:02d}"},
    )

    assert response.status_code == 200
    backlog = next(
        item for item in response.json()["columns"] if item["system_type"] == "backlog"
    )
    titles = {item["title"] for item in backlog["tasks"]}
    assert titles == {"Weekless", "Week task"}


@pytest.mark.django_db
def test_task_events_endpoint(api_client_auth, backlog_column):
    client, _api_key = api_client_auth
    create_response = create_task(
        client,
        title="History",
        column_id=backlog_column.id,
    )
    task_id = create_response.json()["id"]

    response = client.get(reverse("task-events", args=[task_id]))

    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["event_type"] == TaskEventType.CREATED


@pytest.mark.django_db
def test_cannot_deactivate_column_with_active_tasks(api_client_auth, backlog_column):
    client, _api_key = api_client_auth
    create_task(client, title="Blocker", column_id=backlog_column.id)

    response = client.delete(reverse("column-detail", args=[backlog_column.id]))

    assert response.status_code == 409
    assert BoardColumn.objects.filter(pk=backlog_column.id, is_active=True).exists()


@pytest.mark.django_db
def test_current_week_endpoint(api_client_auth):
    client, _api_key = api_client_auth

    response = client.get(reverse("week-current"))

    assert response.status_code == 200
    data = response.json()
    assert data["iso_year"] >= 2026
    assert 1 <= data["iso_week"] <= 53
