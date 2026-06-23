import pytest
from django.urls import reverse

from conftest import create_task_via_api


@pytest.mark.django_db
def test_boards_ec_column_crud_success(api_client):
    created = api_client.post(
        reverse("column-list"),
        {"name": "QA", "color": "blue", "wip_limit": 3},
        content_type="application/json",
    )
    assert created.status_code == 201
    column_id = created.json()["id"]
    updated = api_client.patch(
        reverse("column-detail", args=[column_id]),
        {"name": "QA Updated", "wip_limit": None},
        content_type="application/json",
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "QA Updated"
    deleted = api_client.delete(reverse("column-detail", args=[column_id]))
    assert deleted.status_code == 204


@pytest.mark.django_db
def test_boards_ec_reorder_complete_set_succeeds(api_client):
    listed = api_client.get(reverse("column-list"))
    ids = [item["id"] for item in listed.json()]
    reordered = api_client.post(
        reverse("column-reorder"),
        {"column_ids": list(reversed(ids))},
        content_type="application/json",
    )
    assert reordered.status_code == 200
    assert [item["id"] for item in reordered.json()] == list(reversed(ids))


@pytest.mark.django_db
def test_boards_ec_reorder_partial_set_rejected(api_client):
    listed = api_client.get(reverse("column-list"))
    ids = [item["id"] for item in listed.json()]
    response = api_client.post(
        reverse("column-reorder"),
        {"column_ids": ids[:-1]},
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_boards_ec_reorder_unknown_id_rejected(api_client):
    listed = api_client.get(reverse("column-list"))
    ids = [item["id"] for item in listed.json()]
    response = api_client.post(
        reverse("column-reorder"),
        {"column_ids": ids[:-1] + [999999]},
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_boards_ec_deactivate_done_column_forbidden(api_client, done_column):
    response = api_client.delete(reverse("column-detail", args=[done_column.id]))
    assert response.status_code == 400


@pytest.mark.django_db
def test_boards_ec_deactivate_column_with_tasks_forbidden(api_client, planned_column):
    created = create_task_via_api(
        api_client,
        title="Task in planned",
        column_id=planned_column.id,
    )
    assert created.status_code == 201
    deleted = api_client.delete(reverse("column-detail", args=[planned_column.id]))
    assert deleted.status_code == 409


@pytest.mark.django_db
def test_boards_ec_deactivate_empty_column_allowed(api_client):
    created = api_client.post(
        reverse("column-list"),
        {"name": "Empty removable"},
        content_type="application/json",
    )
    assert created.status_code == 201
    deleted = api_client.delete(reverse("column-detail", args=[created.json()["id"]]))
    assert deleted.status_code == 204


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("wip_limit", "expected_status"),
    [
        pytest.param(1, 201, id="ec_wip_limit_min_boundary_valid"),
        pytest.param(100, 201, id="ec_wip_limit_large_valid"),
        pytest.param(0, 400, id="ec_wip_limit_zero_invalid"),
    ],
)
def test_boards_ec_wip_limit_boundaries_on_create(
    api_client, wip_limit, expected_status
):
    response = api_client.post(
        reverse("column-list"),
        {"name": f"WIP {wip_limit}", "wip_limit": wip_limit},
        content_type="application/json",
    )
    assert response.status_code == expected_status
