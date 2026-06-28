import pytest
from django.urls import reverse
from django.utils import timezone

from apps.tasks.models import Task
from conftest import close_task_via_api, create_task_via_api


@pytest.mark.django_db
def test_tasks_ec_create_without_week_or_tags_uses_defaults(api_client, planned_column):
    response = create_task_via_api(
        api_client,
        title="Default task",
        column_id=planned_column.id,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Default task"
    assert payload["tags"] == []


@pytest.mark.django_db
def test_tasks_ec_create_with_week_and_tags_succeeds(
    api_client, planned_column, week_key, make_tag
):
    make_tag("Urgent", slug="urgent")
    response = create_task_via_api(
        api_client,
        title="Tagged task",
        column_id=planned_column.id,
        week=week_key,
        tags=["urgent"],
    )
    assert response.status_code == 201
    assert response.json()["week"]["iso_week"] >= 1
    assert response.json()["tags"][0]["slug"] == "urgent"


@pytest.mark.django_db
def test_tasks_ec_unknown_tag_rejected(api_client, planned_column):
    response = create_task_via_api(
        api_client,
        title="Unknown tag",
        column_id=planned_column.id,
        tags=["missing-tag"],
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_tasks_ec_move_within_same_column_reorders_positions(
    api_client, planned_column
):
    first = create_task_via_api(api_client, title="T1", column_id=planned_column.id)
    second = create_task_via_api(api_client, title="T2", column_id=planned_column.id)
    assert first.status_code == 201 and second.status_code == 201
    move = api_client.post(
        reverse("task-move", args=[second.json()["id"]]),
        {"target_column_id": planned_column.id, "target_position": 0},
        content_type="application/json",
    )
    assert move.status_code == 200
    assert move.json()["position"] == 0


@pytest.mark.django_db
def test_tasks_ec_move_between_columns_updates_column(
    api_client, planned_column, in_progress_column
):
    from apps.boards.models import TaskStatus
    from apps.tasks.models import Task

    created = create_task_via_api(
        api_client,
        title="Move me",
        column_id=planned_column.id,
        description="Ready for development",
    )
    task = Task.objects.get(pk=created.json()["id"])
    ready_status = TaskStatus.objects.get(
        board=task.board,
        slug="ready_on_develop",
    )
    task.task_status = ready_status
    task.save(update_fields=["task_status", "updated_at"])

    moved = api_client.post(
        reverse("task-move", args=[task.id]),
        {"target_column_id": in_progress_column.id, "target_position": 0},
        content_type="application/json",
    )
    assert moved.status_code == 200
    assert moved.json()["column_id"] == in_progress_column.id


@pytest.mark.django_db
def test_tasks_ec_move_open_to_in_progress_rejected_with_status_error(
    api_client, planned_column, in_progress_column
):
    created = create_task_via_api(
        api_client,
        title="Open in backlog",
        column_id=planned_column.id,
    )
    response = api_client.post(
        reverse("task-move", args=[created.json()["id"]]),
        {"target_column_id": in_progress_column.id, "target_position": 0},
        content_type="application/json",
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "status_column_move_not_allowed"
    assert payload["from_status"]
    assert payload["to_column"]


@pytest.mark.django_db
def test_tasks_ec_move_rejected_when_transition_not_allowed(
    api_client, planned_column, in_progress_column, ready_column
):
    created = create_task_via_api(
        api_client,
        title="Blocked move",
        column_id=planned_column.id,
        description="Filled description",
    )
    allowed_cancel = api_client.post(
        reverse("task-move", args=[created.json()["id"]]),
        {"target_column_id": ready_column.id, "target_position": 0},
        content_type="application/json",
    )
    assert allowed_cancel.status_code == 200
    assert allowed_cancel.json()["column_id"] == ready_column.id
    from apps.boards.models import TaskStatus

    cancel_status = TaskStatus.objects.get(slug="cancel")
    assert allowed_cancel.json()["task_status_id"] == cancel_status.id

    blocked_wip = api_client.post(
        reverse("task-move", args=[created.json()["id"]]),
        {"target_column_id": in_progress_column.id, "target_position": 0},
        content_type="application/json",
    )
    assert blocked_wip.status_code == 400


@pytest.mark.django_db
def test_tasks_ec_move_in_progress_to_ready_uses_done_status(
    api_client, planned_column, in_progress_column, ready_column
):
    from apps.boards.models import TaskStatus
    from apps.tasks.models import Task

    created = create_task_via_api(
        api_client,
        title="Finish from wip",
        column_id=planned_column.id,
        description="Ready for development",
    )
    task = Task.objects.get(pk=created.json()["id"])
    process_status = TaskStatus.objects.get(board=task.board, slug="process")
    task.task_status = process_status
    task.column = in_progress_column
    task.save(update_fields=["task_status", "column", "updated_at"])

    moved = api_client.post(
        reverse("task-move", args=[task.id]),
        {"target_column_id": ready_column.id, "target_position": 0},
        content_type="application/json",
    )
    assert moved.status_code == 200
    done_status = TaskStatus.objects.get(board=task.board, slug="done")
    assert moved.json()["task_status_id"] == done_status.id
    assert moved.json()["column_id"] == ready_column.id


@pytest.mark.django_db
def test_tasks_ec_status_change_open_to_cancel_succeeds(
    api_client, planned_column, ready_column
):
    from apps.boards.models import TaskStatus

    created = create_task_via_api(
        api_client,
        title="Cancel me",
        column_id=planned_column.id,
    )
    task_id = created.json()["id"]
    cancel_status = TaskStatus.objects.get(slug="cancel")

    updated = api_client.patch(
        reverse("task-detail", args=[task_id]),
        {"task_status_id": cancel_status.id},
        content_type="application/json",
    )
    assert updated.status_code == 200
    assert updated.json()["task_status_id"] == cancel_status.id
    assert updated.json()["column_id"] == ready_column.id


@pytest.mark.django_db
def test_tasks_ec_workflow_move_to_in_progress_after_ready_on_develop(
    api_client, planned_column, in_progress_column
):
    from apps.boards.models import TaskStatus
    from apps.tasks.models import Task

    created = create_task_via_api(
        api_client,
        title="Workflow move",
        column_id=planned_column.id,
        description="Ready for development",
    )
    task = Task.objects.get(pk=created.json()["id"])
    ready_status = TaskStatus.objects.get(
        board=task.board,
        slug="ready_on_develop",
    )
    task.task_status = ready_status
    task.save(update_fields=["task_status", "updated_at"])

    allowed = api_client.post(
        reverse("task-move", args=[task.id]),
        {"target_column_id": in_progress_column.id, "target_position": 0},
        content_type="application/json",
    )
    assert allowed.status_code == 200
    assert allowed.json()["column_id"] == in_progress_column.id


@pytest.mark.django_db
def test_tasks_ec_negative_move_position_rejected(api_client, planned_column):
    created = create_task_via_api(
        api_client, title="Bad move", column_id=planned_column.id
    )
    response = api_client.post(
        reverse("task-move", args=[created.json()["id"]]),
        {"target_column_id": planned_column.id, "target_position": -1},
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_tasks_ec_close_reopen_lifecycle_succeeds(api_client, planned_column):
    created = create_task_via_api(
        api_client, title="Lifecycle", column_id=planned_column.id
    )
    task_id = created.json()["id"]
    closed = close_task_via_api(api_client, task_id)
    assert closed.status_code == 200
    assert closed.json()["archived_at"] is not None
    reopened = api_client.post(reverse("task-reopen", args=[task_id]))
    assert reopened.status_code == 200
    assert reopened.json()["archived_at"] is None


@pytest.mark.django_db
def test_tasks_ec_archived_task_update_rejected(api_client, planned_column):
    created = create_task_via_api(
        api_client, title="Archived update", column_id=planned_column.id
    )
    task_id = created.json()["id"]
    close_task_via_api(api_client, task_id)
    response = api_client.patch(
        reverse("task-detail", args=[task_id]),
        {"title": "Should fail"},
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_tasks_ec_board_endpoint_returns_columns_and_tasks(api_client, planned_column):
    create_task_via_api(api_client, title="On board", column_id=planned_column.id)
    response = api_client.get(reverse("board"))
    assert response.status_code == 200
    body = response.json()
    assert "columns" in body
    assert len(body["columns"]) >= 1


@pytest.mark.django_db
def test_tasks_ec_events_endpoint_lists_task_events(api_client, planned_column):
    created = create_task_via_api(
        api_client, title="Events task", column_id=planned_column.id
    )
    task_id = created.json()["id"]
    close_task_via_api(api_client, task_id)
    events = api_client.get(reverse("task-events", args=[task_id]))
    assert events.status_code == 200
    assert len(events.json()) >= 2


@pytest.mark.django_db
def test_tasks_ec_task_list_filters_by_week(api_client, planned_column, week_key):
    create_task_via_api(
        api_client, title="With week", column_id=planned_column.id, week=week_key
    )
    create_task_via_api(api_client, title="Without week", column_id=planned_column.id)
    response = api_client.get(reverse("task-list"), {"week": week_key})
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert "With week" in titles
    assert "Without week" in titles


@pytest.mark.django_db
def test_tasks_ec_close_moves_to_terminal_column(
    api_client, planned_column, ready_column
):
    created = create_task_via_api(
        api_client,
        title="Close to terminal",
        column_id=planned_column.id,
    )
    task_id = created.json()["id"]
    close_task_via_api(api_client, task_id)
    task = Task.objects.get(pk=task_id)
    assert task.column_id == ready_column.id


@pytest.mark.django_db
def test_tasks_ec_close_task_sets_archive_timestamps(api_client, planned_column):
    created = create_task_via_api(
        api_client, title="Close timestamp", column_id=planned_column.id
    )
    task_id = created.json()["id"]
    close_task_via_api(api_client, task_id)
    task = Task.objects.get(pk=task_id)
    assert task.closed_at is not None
    assert task.archived_at is not None
    assert task.closed_at <= timezone.now()


@pytest.mark.django_db
def test_tasks_ec_create_with_story_points(api_client, planned_column):
    response = api_client.post(
        reverse("task-list"),
        {
            "title": "With points",
            "column_id": planned_column.id,
            "task_type": "task",
            "story_points": 5,
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["story_points"] == 5

    board = api_client.get(reverse("board"))
    assert board.status_code == 200
    tasks = [
        task
        for column in board.json()["columns"]
        for task in column["tasks"]
        if task["id"] == payload["id"]
    ]
    assert len(tasks) == 1
    assert tasks[0]["story_points"] == 5


@pytest.mark.django_db
def test_tasks_ec_create_requires_task_type(api_client, planned_column):
    response = api_client.post(
        reverse("task-list"),
        {"title": "No type", "column_id": planned_column.id},
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_tasks_ec_create_with_task_type_and_links(api_client, planned_column):
    target = create_task_via_api(
        api_client,
        title="Target",
        column_id=planned_column.id,
        task_type="story",
    )
    assert target.status_code == 201

    response = create_task_via_api(
        api_client,
        title="Blocker",
        column_id=planned_column.id,
        task_type="bug",
        links=[
            {
                "target_task_id": target.json()["id"],
                "link_type": "blocks",
            },
        ],
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["task_type"] == "bug"
    outgoing = [link for link in payload["links"] if link["direction"] == "outgoing"]
    assert len(outgoing) == 1
    assert outgoing[0]["link_type"] == "blocks"
    assert outgoing[0]["task_id"] == target.json()["id"]


@pytest.mark.django_db
def test_tasks_ec_update_task_type_and_sync_links(api_client, planned_column):
    first = create_task_via_api(
        api_client,
        title="First",
        column_id=planned_column.id,
        task_type="task",
    )
    second = create_task_via_api(
        api_client,
        title="Second",
        column_id=planned_column.id,
        task_type="epic",
    )
    task_id = first.json()["id"]
    second_id = second.json()["id"]

    patch = api_client.patch(
        reverse("task-detail", args=[task_id]),
        {
            "task_type": "story",
            "links": [{"target_task_id": second_id, "link_type": "relates"}],
        },
        content_type="application/json",
    )
    assert patch.status_code == 200
    payload = patch.json()
    assert payload["task_type"] == "story"
    outgoing = [link for link in payload["links"] if link["direction"] == "outgoing"]
    assert len(outgoing) == 1
    assert outgoing[0]["task_id"] == second_id

    clear = api_client.patch(
        reverse("task-detail", args=[task_id]),
        {"links": []},
        content_type="application/json",
    )
    assert clear.status_code == 200
    assert clear.json()["links"] == []


@pytest.mark.django_db
def test_tasks_ec_search_tasks_for_link_picker(api_client, planned_column):
    create_task_via_api(
        api_client,
        title="Alpha release",
        column_id=planned_column.id,
        task_type="epic",
    )
    blocker = create_task_via_api(
        api_client,
        title="Beta blocker",
        column_id=planned_column.id,
        task_type="bug",
    )

    response = api_client.get(
        reverse("task-list"),
        {"q": "beta", "exclude": blocker.json()["id"]},
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()]
    assert "Beta blocker" not in titles
    assert "Alpha release" not in titles
