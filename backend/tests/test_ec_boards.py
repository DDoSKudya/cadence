import pytest
from django.urls import reverse

from apps.boards.models import SystemType
from conftest import create_task_via_api


def column_items(response):
    payload = response.json()
    if isinstance(payload, dict) and "columns" in payload:
        return payload["columns"]
    return payload


@pytest.mark.django_db
def test_boards_ec_column_list_returns_default_scheme(api_client):
    response = api_client.get(reverse("column-list"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["scheme"]["slug"] == "default"
    assert payload["scheme"]["is_locked"] is True
    assert payload["limits"]["max_columns"] == 7
    columns = payload["columns"]
    assert len(columns) == 3
    assert [column["system_type"] for column in columns] == [
        SystemType.BACKLOG,
        SystemType.IN_PROGRESS,
        SystemType.READY,
    ]
    assert all(column["is_locked"] for column in columns)


@pytest.mark.django_db
def test_boards_ec_locked_scheme_rejects_column_create(api_client):
    response = api_client.post(
        reverse("column-list"),
        {"name": "QA", "color": "blue", "wip_limit": 3},
        content_type="application/json",
    )
    assert response.status_code in {400, 403}


@pytest.mark.django_db
def test_boards_ec_locked_scheme_rejects_column_update(api_client, planned_column):
    response = api_client.patch(
        reverse("column-detail", args=[planned_column.id]),
        {"name": "QA Updated"},
        content_type="application/json",
    )
    assert response.status_code in {400, 403}


@pytest.mark.django_db
def test_boards_ec_locked_scheme_rejects_reorder(api_client):
    listed = api_client.get(reverse("column-list"))
    ids = [item["id"] for item in column_items(listed)]
    response = api_client.post(
        reverse("column-reorder"),
        {"column_ids": list(reversed(ids))},
        content_type="application/json",
    )
    assert response.status_code in {400, 403}


@pytest.mark.django_db
def test_boards_ec_locked_scheme_rejects_column_delete(api_client, ready_column):
    response = api_client.delete(reverse("column-detail", args=[ready_column.id]))
    assert response.status_code in {400, 403}


@pytest.mark.django_db
def test_boards_ec_deactivate_column_with_tasks_forbidden(api_client, planned_column):
    created = create_task_via_api(
        api_client,
        title="Task in backlog",
        column_id=planned_column.id,
    )
    assert created.status_code == 201
    deleted = api_client.delete(reverse("column-detail", args=[planned_column.id]))
    assert deleted.status_code in {400, 403}


@pytest.mark.django_db
def test_boards_ec_workflow_default_scheme_is_enforced(
    api_client, planned_column, in_progress_column, ready_column
):
    response = api_client.get(reverse("column-workflow"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["enforced"] is True
    assert payload["transitions"] == [
        {
            "from_column_id": planned_column.id,
            "to_column_id": in_progress_column.id,
        },
        {
            "from_column_id": in_progress_column.id,
            "to_column_id": ready_column.id,
        },
    ]


@pytest.mark.django_db
def test_boards_ec_locked_scheme_rejects_workflow_update(
    api_client, planned_column, ready_column
):
    response = api_client.put(
        reverse("column-workflow"),
        {
            "transitions": [
                {
                    "from_column_id": planned_column.id,
                    "to_column_id": ready_column.id,
                },
            ],
        },
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_boards_ec_custom_scheme_workflow_persists_across_switch(api_client):
    created = api_client.post(
        reverse("board-scheme-list"),
        {
            "name": "Workflow scheme",
            "switch": True,
            "confirm": True,
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    custom_slug = created.json()["scheme"]["slug"]

    for index, (name, system_type, color) in enumerate(
        [
            ("Backlog", SystemType.BACKLOG, "slate"),
            ("Doing", SystemType.IN_PROGRESS, "amber"),
            ("Done", SystemType.READY, "green"),
        ],
    ):
        response = api_client.post(
            reverse("column-list"),
            {
                "name": name,
                "color": color,
                "system_type": system_type,
                "position": index,
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    listed = api_client.get(reverse("column-list"))
    columns = column_items(listed)
    assert len(columns) == 3
    backlog_id = columns[0]["id"]
    doing_id = columns[1]["id"]
    done_id = columns[2]["id"]

    saved = api_client.put(
        reverse("column-workflow"),
        {
            "transitions": [
                {"from_column_id": backlog_id, "to_column_id": doing_id},
                {"from_column_id": doing_id, "to_column_id": done_id},
            ],
        },
        content_type="application/json",
    )
    assert saved.status_code == 200
    assert saved.json()["enforced"] is True

    switched = api_client.post(
        reverse("board-scheme-switch"),
        {"slug": "default", "confirm": True},
        content_type="application/json",
    )
    assert switched.status_code == 200

    restored = api_client.post(
        reverse("board-scheme-switch"),
        {"slug": custom_slug, "confirm": True},
        content_type="application/json",
    )
    assert restored.status_code == 200
    payload = restored.json()
    assert payload["scheme"]["slug"] == custom_slug
    assert payload["workflow"]["enforced"] is True
    restored_columns = {column["name"]: column["id"] for column in payload["columns"]}
    assert payload["workflow"]["transitions"] == [
        {
            "from_column_id": restored_columns["Backlog"],
            "to_column_id": restored_columns["Doing"],
        },
        {
            "from_column_id": restored_columns["Doing"],
            "to_column_id": restored_columns["Done"],
        },
    ]


@pytest.mark.django_db
def test_boards_ec_custom_scheme_status_graph_persists_across_switch(api_client):
    created = api_client.post(
        reverse("board-scheme-list"),
        {
            "name": "Status graph scheme",
            "switch": True,
            "confirm": True,
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    custom_slug = created.json()["scheme"]["slug"]

    for index, (name, system_type, color) in enumerate(
        [
            ("Backlog", SystemType.BACKLOG, "slate"),
            ("Doing", SystemType.IN_PROGRESS, "amber"),
            ("Done", SystemType.READY, "green"),
        ],
    ):
        response = api_client.post(
            reverse("column-list"),
            {
                "name": name,
                "color": color,
                "system_type": system_type,
                "position": index,
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    columns = {
        column["system_type"]: column
        for column in column_items(api_client.get(reverse("column-list")))
    }
    graph = api_client.get(reverse("task-status-graph")).json()
    open_status = next(item for item in graph["statuses"] if item["slug"] == "open")
    process_status = next(
        item for item in graph["statuses"] if item["slug"] == "process"
    )

    saved = api_client.put(
        reverse("task-status-graph"),
        {
            "statuses": [
                {
                    "id": open_status["id"],
                    "name": open_status["name"],
                    "color": open_status["color"],
                    "layout_x": 120,
                    "layout_y": 80,
                    "is_initial": True,
                    "is_terminal": False,
                    "column_id": columns[SystemType.BACKLOG]["id"],
                    "rules": open_status["rules"],
                },
                {
                    "id": process_status["id"],
                    "name": process_status["name"],
                    "color": process_status["color"],
                    "layout_x": 420,
                    "layout_y": 80,
                    "is_initial": False,
                    "is_terminal": False,
                    "column_id": columns[SystemType.IN_PROGRESS]["id"],
                    "rules": process_status["rules"],
                },
            ],
            "transitions": [
                {
                    "from_status_id": str(open_status["id"]),
                    "to_status_id": str(process_status["id"]),
                },
            ],
        },
        content_type="application/json",
    )
    assert saved.status_code == 200
    assert saved.json()["enforced"] is True
    assert len(saved.json()["transitions"]) == 1

    switched = api_client.post(
        reverse("board-scheme-switch"),
        {"slug": "default", "confirm": True},
        content_type="application/json",
    )
    assert switched.status_code == 200

    restored = api_client.post(
        reverse("board-scheme-switch"),
        {"slug": custom_slug, "confirm": True},
        content_type="application/json",
    )
    assert restored.status_code == 200
    payload = restored.json()
    assert payload["scheme"]["slug"] == custom_slug
    flow_statuses = [
        item for item in payload["status_graph"]["statuses"] if item["on_flow"]
    ]
    assert len(flow_statuses) == 2
    assert payload["status_graph"]["enforced"] is True
    assert len(payload["status_graph"]["transitions"]) == 1
    slugs = {item["slug"] for item in flow_statuses}
    assert slugs == {"open", "process"}


@pytest.mark.django_db
def test_boards_ec_scheme_list_includes_default(api_client):
    response = api_client.get(reverse("board-scheme-list"))
    assert response.status_code == 200
    payload = response.json()
    slugs = [item["slug"] for item in payload["schemes"]]
    assert "default" in slugs
    assert payload["limits"]["max_schemes"] == 4
    assert payload["limits"]["max_columns"] == 7


@pytest.mark.django_db
def test_boards_ec_scheme_switch_deletes_tasks(
    api_client, planned_column, in_progress_column
):
    created = create_task_via_api(
        api_client,
        title="Will be deleted",
        column_id=planned_column.id,
    )
    assert created.status_code == 201

    switched = api_client.post(
        reverse("board-scheme-switch"),
        {"slug": "default", "confirm": True},
        content_type="application/json",
    )
    assert switched.status_code == 200
    assert len(switched.json()["columns"]) == 3

    listed = api_client.get(reverse("task-list"))
    assert listed.status_code == 200
    assert listed.json() == []


@pytest.mark.django_db
def test_boards_ec_create_custom_scheme_and_add_column(api_client):
    created = api_client.post(
        reverse("board-scheme-list"),
        {
            "name": "Team board",
            "description": "Custom workflow",
            "switch": True,
            "confirm": True,
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["scheme"]["slug"]
    assert payload["scheme"]["is_locked"] is False
    assert payload["columns"] == []

    column = api_client.post(
        reverse("column-list"),
        {"name": "Ideas", "color": "blue", "system_type": "backlog"},
        content_type="application/json",
    )
    assert column.status_code == 201

    listed = api_client.get(reverse("column-list"))
    assert len(column_items(listed)) == 1
    assert column_items(listed)[0]["name"] == "Ideas"


@pytest.mark.django_db
def test_boards_ec_delete_inactive_custom_scheme(api_client):
    created = api_client.post(
        reverse("board-scheme-list"),
        {
            "name": "Disposable",
            "switch": False,
            "confirm": False,
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    slug = created.json()["slug"]

    deleted = api_client.delete(
        reverse("board-scheme-detail", kwargs={"slug": slug}),
        {"confirm": True},
        content_type="application/json",
    )
    assert deleted.status_code == 204

    listed = api_client.get(reverse("board-scheme-list"))
    slugs = [item["slug"] for item in listed.json()["schemes"]]
    assert slug not in slugs


@pytest.mark.django_db
def test_boards_ec_delete_active_custom_scheme_switches_to_default(api_client):
    created = api_client.post(
        reverse("board-scheme-list"),
        {
            "name": "Temporary",
            "switch": True,
            "confirm": True,
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    slug = created.json()["scheme"]["slug"]

    column = api_client.post(
        reverse("column-list"),
        {"name": "Ideas", "color": "blue", "system_type": "backlog"},
        content_type="application/json",
    )
    assert column.status_code == 201
    column_id = column.json()["id"]

    task = create_task_via_api(
        api_client,
        title="Will be deleted",
        column_id=column_id,
    )
    assert task.status_code == 201

    deleted = api_client.delete(
        reverse("board-scheme-detail", kwargs={"slug": slug}),
        {"confirm": True},
        content_type="application/json",
    )
    assert deleted.status_code == 204

    columns = api_client.get(reverse("column-list"))
    assert columns.json()["scheme"]["slug"] == "default"
    assert len(column_items(columns)) == 3

    listed = api_client.get(reverse("task-list"))
    assert listed.json() == []


@pytest.mark.django_db
def test_boards_ec_delete_default_scheme_is_forbidden(api_client):
    response = api_client.delete(
        reverse("board-scheme-detail", kwargs={"slug": "default"}),
        {"confirm": True},
        content_type="application/json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_boards_ec_scheme_limit_blocks_create(api_client):
    for index in range(3):
        created = api_client.post(
            reverse("board-scheme-list"),
            {
                "name": f"Scheme {index}",
                "switch": False,
                "confirm": False,
            },
            content_type="application/json",
        )
        assert created.status_code == 201

    blocked = api_client.post(
        reverse("board-scheme-list"),
        {
            "name": "One too many",
            "switch": False,
            "confirm": False,
        },
        content_type="application/json",
    )
    assert blocked.status_code == 400


@pytest.mark.django_db
def test_boards_ec_column_limit_blocks_create(api_client):
    created = api_client.post(
        reverse("board-scheme-list"),
        {
            "name": "Wide board",
            "switch": True,
            "confirm": True,
        },
        content_type="application/json",
    )
    assert created.status_code == 201

    for index in range(7):
        column = api_client.post(
            reverse("column-list"),
            {"name": f"Column {index}", "color": "blue", "system_type": "backlog"},
            content_type="application/json",
        )
        assert column.status_code == 201

    blocked = api_client.post(
        reverse("column-list"),
        {"name": "Overflow", "color": "blue", "system_type": "backlog"},
        content_type="application/json",
    )
    assert blocked.status_code == 400


@pytest.mark.django_db
def test_boards_ec_status_workflow_default_scheme_is_enforced(
    api_client, planned_column, in_progress_column, ready_column
):
    response = api_client.get(reverse("task-status-graph"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["enforced"] is True
    statuses_by_slug = {item["slug"]: item for item in payload["statuses"]}
    expected_slugs = {
        "open",
        "ready_on_develop",
        "process",
        "testing",
        "done",
        "cancel",
    }
    assert expected_slugs.issubset(statuses_by_slug)
    assert all(item["on_flow"] for item in payload["statuses"])
    assert statuses_by_slug["open"]["is_initial"] is True
    assert statuses_by_slug["done"]["is_terminal"] is True
    assert statuses_by_slug["cancel"]["is_terminal"] is True
    assert statuses_by_slug["open"]["column_id"] == planned_column.id
    assert statuses_by_slug["process"]["column_id"] == in_progress_column.id
    assert statuses_by_slug["done"]["column_id"] == ready_column.id
    transition_pairs = {
        (item["from_status_id"], item["to_status_id"])
        for item in payload["transitions"]
    }
    assert (
        statuses_by_slug["open"]["id"],
        statuses_by_slug["ready_on_develop"]["id"],
    ) in transition_pairs
    assert (
        statuses_by_slug["testing"]["id"],
        statuses_by_slug["done"]["id"],
    ) in transition_pairs
    assert (
        statuses_by_slug["process"]["id"],
        statuses_by_slug["cancel"]["id"],
    ) in transition_pairs


@pytest.mark.django_db
def test_boards_ec_custom_scheme_starts_with_library_statuses_only(api_client):
    created = api_client.post(
        reverse("board-scheme-list"),
        {
            "name": "Library only",
            "description": "Custom workflow",
            "switch": True,
            "confirm": True,
        },
        content_type="application/json",
    )
    assert created.status_code == 201

    response = api_client.get(reverse("task-status-graph"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["enforced"] is False
    assert payload["transitions"] == []
    assert len(payload["statuses"]) == 6
    assert all(not item["on_flow"] for item in payload["statuses"])


@pytest.mark.django_db
def test_boards_ec_locked_scheme_rejects_status_workflow_update(
    api_client, planned_column, ready_column
):
    graph = api_client.get(reverse("task-status-graph")).json()
    statuses = graph["statuses"]
    backlog = next(item for item in statuses if item["slug"] == "open")
    ready = next(item for item in statuses if item["slug"] == "done")
    response = api_client.put(
        reverse("task-status-graph"),
        {
            "statuses": statuses,
            "transitions": [
                {
                    "from_status_id": str(backlog["id"]),
                    "to_status_id": str(ready["id"]),
                },
            ],
        },
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_boards_ec_locked_scheme_allows_status_layout_update(api_client):
    graph = api_client.get(reverse("task-status-graph")).json()
    statuses = [
        {
            "id": item["id"],
            "layout_x": float(item["layout_x"]) + 40,
            "layout_y": float(item["layout_y"]) + 20,
        }
        for item in graph["statuses"]
    ]
    response = api_client.patch(
        reverse("task-status-graph"),
        {"statuses": statuses},
        content_type="application/json",
    )
    assert response.status_code == 200
    payload = response.json()
    updated = {item["id"]: item for item in payload["statuses"]}
    for item in statuses:
        assert updated[item["id"]]["layout_x"] == item["layout_x"]
        assert updated[item["id"]]["layout_y"] == item["layout_y"]


@pytest.mark.django_db
def test_boards_ec_tags_are_scoped_to_active_scheme(api_client, board, make_tag):
    from apps.boards.scheme_services import BoardSchemeService
    from apps.core.models import Tag

    make_tag("Default tag", slug="default-tag")
    custom = BoardSchemeService.create_custom_scheme(name="Tags EC custom")
    Tag.objects.create(scheme=custom, name="Custom tag", slug="custom-tag")

    listed_default = api_client.get(reverse("tag-list")).json()
    assert any(item["slug"] == "default-tag" for item in listed_default)
    assert not any(item["slug"] == "custom-tag" for item in listed_default)

    BoardSchemeService.switch_scheme(board, custom.slug)
    listed_custom = api_client.get(reverse("tag-list")).json()
    assert any(item["slug"] == "custom-tag" for item in listed_custom)
    assert not any(item["slug"] == "default-tag" for item in listed_custom)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("wip_limit", "expected_status"),
    [
        pytest.param(1, 403, id="ec_wip_limit_locked_scheme"),
        pytest.param(0, 403, id="ec_wip_limit_locked_scheme_invalid"),
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
    assert response.status_code in {400, 403}


@pytest.mark.django_db
def test_boards_ec_scheme_switch_requires_confirm(api_client):
    response = api_client.post(
        reverse("board-scheme-switch"),
        {"slug": "default", "confirm": False},
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_boards_ec_status_graph_bindings_persist_after_column_reorder(api_client):
    created = api_client.post(
        reverse("board-scheme-list"),
        {"name": "Reorder bindings", "switch": True, "confirm": True},
        content_type="application/json",
    )
    assert created.status_code == 201
    custom_slug = created.json()["scheme"]["slug"]

    for index, (name, system_type, color) in enumerate(
        [
            ("Backlog", SystemType.BACKLOG, "slate"),
            ("Doing", SystemType.IN_PROGRESS, "amber"),
            ("Done", SystemType.READY, "green"),
        ],
    ):
        response = api_client.post(
            reverse("column-list"),
            {
                "name": name,
                "color": color,
                "system_type": system_type,
                "position": index,
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    columns = column_items(api_client.get(reverse("column-list")))
    columns_by_name = {column["name"]: column for column in columns}
    graph = api_client.get(reverse("task-status-graph")).json()
    open_status = next(item for item in graph["statuses"] if item["slug"] == "open")
    process_status = next(
        item for item in graph["statuses"] if item["slug"] == "process"
    )

    saved = api_client.put(
        reverse("task-status-graph"),
        {
            "statuses": [
                {
                    "id": open_status["id"],
                    "name": open_status["name"],
                    "color": open_status["color"],
                    "layout_x": 120,
                    "layout_y": 80,
                    "is_initial": True,
                    "is_terminal": False,
                    "column_id": columns_by_name["Backlog"]["id"],
                    "rules": open_status["rules"],
                },
                {
                    "id": process_status["id"],
                    "name": process_status["name"],
                    "color": process_status["color"],
                    "layout_x": 420,
                    "layout_y": 80,
                    "is_initial": False,
                    "is_terminal": False,
                    "column_id": columns_by_name["Doing"]["id"],
                    "rules": process_status["rules"],
                },
            ],
            "transitions": [
                {
                    "from_status_id": str(open_status["id"]),
                    "to_status_id": str(process_status["id"]),
                },
            ],
        },
        content_type="application/json",
    )
    assert saved.status_code == 200

    reordered = api_client.post(
        reverse("column-reorder"),
        {
            "column_ids": [
                columns_by_name["Doing"]["id"],
                columns_by_name["Backlog"]["id"],
                columns_by_name["Done"]["id"],
            ],
        },
        content_type="application/json",
    )
    assert reordered.status_code == 200

    switched = api_client.post(
        reverse("board-scheme-switch"),
        {"slug": "default", "confirm": True},
        content_type="application/json",
    )
    assert switched.status_code == 200

    restored = api_client.post(
        reverse("board-scheme-switch"),
        {"slug": custom_slug, "confirm": True},
        content_type="application/json",
    )
    assert restored.status_code == 200

    payload = restored.json()
    restored_columns = {column["name"]: column["id"] for column in payload["columns"]}
    flow_statuses = {
        item["slug"]: item
        for item in payload["status_graph"]["statuses"]
        if item["on_flow"]
    }
    assert flow_statuses["open"]["column_id"] == restored_columns["Backlog"]
    assert flow_statuses["process"]["column_id"] == restored_columns["Doing"]


@pytest.mark.django_db
def test_boards_ec_status_graph_transition_rules_persist_across_switch(api_client):
    created = api_client.post(
        reverse("board-scheme-list"),
        {"name": "Rules scheme", "switch": True, "confirm": True},
        content_type="application/json",
    )
    assert created.status_code == 201
    custom_slug = created.json()["scheme"]["slug"]

    for index, (name, system_type, color) in enumerate(
        [
            ("Backlog", SystemType.BACKLOG, "slate"),
            ("Doing", SystemType.IN_PROGRESS, "amber"),
            ("Done", SystemType.READY, "green"),
        ],
    ):
        response = api_client.post(
            reverse("column-list"),
            {
                "name": name,
                "color": color,
                "system_type": system_type,
                "position": index,
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    graph = api_client.get(reverse("task-status-graph")).json()
    open_status = next(item for item in graph["statuses"] if item["slug"] == "open")
    process_status = next(
        item for item in graph["statuses"] if item["slug"] == "process"
    )
    transition_rules = {"required_fields": ["description"]}

    saved = api_client.put(
        reverse("task-status-graph"),
        {
            "statuses": [
                {
                    "id": open_status["id"],
                    "name": open_status["name"],
                    "color": open_status["color"],
                    "layout_x": 120,
                    "layout_y": 80,
                    "is_initial": True,
                    "is_terminal": False,
                    "rules": {"creation_only": True},
                },
                {
                    "id": process_status["id"],
                    "name": process_status["name"],
                    "color": process_status["color"],
                    "layout_x": 420,
                    "layout_y": 80,
                    "is_initial": False,
                    "is_terminal": False,
                    "rules": {},
                },
            ],
            "transitions": [
                {
                    "from_status_id": str(open_status["id"]),
                    "to_status_id": str(process_status["id"]),
                    "rules": transition_rules,
                },
            ],
        },
        content_type="application/json",
    )
    assert saved.status_code == 200

    switched = api_client.post(
        reverse("board-scheme-switch"),
        {"slug": "default", "confirm": True},
        content_type="application/json",
    )
    assert switched.status_code == 200

    restored = api_client.post(
        reverse("board-scheme-switch"),
        {"slug": custom_slug, "confirm": True},
        content_type="application/json",
    )
    assert restored.status_code == 200

    payload = restored.json()
    flow_statuses = {
        item["slug"]: item
        for item in payload["status_graph"]["statuses"]
        if item["on_flow"]
    }
    assert flow_statuses["open"]["rules"]["creation_only"] is True
    restored_transition = payload["status_graph"]["transitions"][0]
    assert restored_transition["rules"] == transition_rules
