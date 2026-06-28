import json
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.boards.models import BoardColumn, SystemType
from apps.boards.services import ColumnSettingsService
from apps.core.models import ApiKey, ProjectSettings
from apps.tasks.models import Task
from apps.weeks.services import WeekService


@pytest.fixture
def api_client(client):
    api_key, raw_key = ApiKey.issue("tests")
    client.defaults["HTTP_AUTHORIZATION"] = f"Api-Key {raw_key}"
    return client


@pytest.fixture
def anon_client(client):
    client.defaults.pop("HTTP_AUTHORIZATION", None)
    return client


@pytest.fixture
def session_client(client, django_user_model):
    user = django_user_model.objects.create_user(username="tester", password="secret")
    client.force_login(user)
    return client


@pytest.fixture
def board():
    return ColumnSettingsService.get_default_board()


@pytest.fixture
def active_scheme(board):
    from apps.boards.scheme_services import BoardSchemeService

    scheme = BoardSchemeService.get_active_scheme(board)
    assert scheme is not None
    return scheme


@pytest.fixture
def make_tag(active_scheme):
    from apps.core.models import Tag

    def _make_tag(name: str, slug: str | None = None, **kwargs):
        return Tag.objects.create(
            scheme=active_scheme,
            name=name,
            slug=slug or name.strip().lower().replace(" ", "-"),
            **kwargs,
        )

    return _make_tag


@pytest.fixture
def backlog_column(board):
    return BoardColumn.objects.get(board=board, system_type=SystemType.BACKLOG)


@pytest.fixture
def planned_column(board):
    return BoardColumn.objects.get(board=board, system_type=SystemType.BACKLOG)


@pytest.fixture
def in_progress_column(board):
    return BoardColumn.objects.get(board=board, system_type=SystemType.IN_PROGRESS)


@pytest.fixture
def ready_column(board):
    return BoardColumn.objects.get(board=board, system_type=SystemType.READY)


@pytest.fixture
def done_column(board):
    return BoardColumn.objects.filter(board=board, system_type=SystemType.DONE).first()


@pytest.fixture
def current_week():
    return WeekService.get_or_create_current_week()


@pytest.fixture
def week_key(current_week):
    return f"{current_week.iso_year}-W{current_week.iso_week:02d}"


@pytest.fixture
def inbox_dirs(tmp_path, settings):
    paths = {}
    for name in ("pending", "processing", "processed", "failed"):
        path = tmp_path / name
        path.mkdir()
        paths[name] = path
    settings.TASK_INBOX_PENDING_DIR = str(paths["pending"])
    settings.TASK_INBOX_PROCESSING_DIR = str(paths["processing"])
    settings.TASK_INBOX_PROCESSED_DIR = str(paths["processed"])
    settings.TASK_INBOX_FAILED_DIR = str(paths["failed"])
    return paths


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def telegram_enabled(settings):
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    project = ProjectSettings.load()
    project.telegram_enabled = True
    project.telegram_bot_token = "test-token"
    project.telegram_recipients = [
        {"chat_id": "12345", "label": "Test", "kind": "user"},
    ]
    project.stale_in_progress_minutes = 60
    project.stale_planned_minutes = 120
    project.default_reminder_interval_minutes = 30
    project.save()
    return project


@pytest.fixture
def stale_task(planned_column):
    return Task.objects.create(
        title="Stale task",
        board=planned_column.board,
        column=planned_column,
        position=0,
        column_entered_at=timezone.now() - timedelta(hours=3),
        reminder_enabled=True,
    )


def create_task_via_api(
    client,
    *,
    title: str,
    column_id: int,
    week: str | None = None,
    tags: list[str] | None = None,
    description: str | None = None,
    task_type: str = "task",
    links: list[dict] | None = None,
):
    payload: dict = {
        "title": title,
        "column_id": column_id,
        "task_type": task_type,
    }
    if week is not None:
        payload["week"] = week
    if tags is not None:
        payload["tags"] = tags
    if description is not None:
        payload["description"] = description
    if links is not None:
        payload["links"] = links
    return client.post(
        reverse("task-list"),
        payload,
        content_type="application/json",
    )


def close_task_via_api(client, task_id: int, **extra):
    payload = {
        "completion_note": "Done",
        **extra,
    }
    return client.post(
        reverse("task-close", args=[task_id]),
        payload,
        content_type="application/json",
    )


def import_payload(**overrides):
    payload = {
        "schema_version": "1.0",
        "idempotency_key": "import-key-1",
        "source": "mentor",
        "tasks": [{"title": "Import task", "column": "planned", "priority": "normal"}],
    }
    payload.update(overrides)
    return payload


def write_json(path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def upload_import(client, payload: dict, name: str = "batch.json"):
    content = json.dumps(payload).encode()
    file = SimpleUploadedFile(name, content, content_type="application/json")
    return client.post(reverse("import-upload"), {"file": file})
