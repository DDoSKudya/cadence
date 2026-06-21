import pytest
from django.urls import reverse

from apps.boards.models import BoardColumn, SystemType
from apps.boards.services import ColumnSettingsService
from apps.core.models import ApiKey


@pytest.fixture
def api_client_auth(client):
    api_key, raw_key = ApiKey.issue("tests")
    client.defaults["HTTP_AUTHORIZATION"] = f"Api-Key {raw_key}"
    return client, api_key


@pytest.mark.django_db
def test_seed_board_has_done_column():
    board = ColumnSettingsService.get_default_board()
    columns = ColumnSettingsService.active_columns(board)

    assert columns.count() == 4
    assert columns.filter(system_type=SystemType.DONE).exists()


@pytest.mark.django_db
def test_reorder_columns(api_client_auth):
    client, _api_key = api_client_auth
    board = ColumnSettingsService.get_default_board()
    columns = list(ColumnSettingsService.active_columns(board))
    reversed_ids = [column.id for column in reversed(columns)]

    response = client.post(
        reverse("column-reorder"),
        {"column_ids": reversed_ids},
        content_type="application/json",
    )

    assert response.status_code == 200
    positions = [item["position"] for item in response.json()]
    assert positions == [0, 1, 2, 3]
    assert [item["id"] for item in response.json()] == reversed_ids


@pytest.mark.django_db
def test_reorder_requires_all_active_columns(api_client_auth):
    client, _api_key = api_client_auth
    board = ColumnSettingsService.get_default_board()
    columns = list(ColumnSettingsService.active_columns(board))

    response = client.post(
        reverse("column-reorder"),
        {"column_ids": [columns[0].id, columns[1].id]},
        content_type="application/json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_deactivate_done_column(api_client_auth):
    client, _api_key = api_client_auth
    done_column = BoardColumn.objects.get(system_type=SystemType.DONE)

    response = client.delete(reverse("column-detail", args=[done_column.id]))

    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_deactivate_last_active_column(api_client_auth):
    client, _api_key = api_client_auth
    board = ColumnSettingsService.get_default_board()
    keep = ColumnSettingsService.active_columns(board).first()
    for column in ColumnSettingsService.active_columns(board).exclude(pk=keep.pk):
        column.is_active = False
        column.save(update_fields=["is_active"])

    response = client.delete(reverse("column-detail", args=[keep.id]))

    assert response.status_code == 400


@pytest.mark.django_db
def test_create_update_and_deactivate_column(api_client_auth):
    client, _api_key = api_client_auth

    create_response = client.post(
        reverse("column-list"),
        {"name": "Review", "color": "violet", "wip_limit": 3},
        content_type="application/json",
    )
    assert create_response.status_code == 201
    column_id = create_response.json()["id"]

    patch_response = client.patch(
        reverse("column-detail", args=[column_id]),
        {"name": "Code Review", "wip_limit": None},
        content_type="application/json",
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Code Review"
    assert patch_response.json()["wip_limit"] is None

    delete_response = client.delete(reverse("column-detail", args=[column_id]))
    assert delete_response.status_code == 204
    assert not BoardColumn.objects.filter(pk=column_id, is_active=True).exists()
