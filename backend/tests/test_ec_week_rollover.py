import pytest
from django.utils import timezone

from apps.boards.models import TaskStatus
from apps.boards.services import ColumnSettingsService
from apps.core.models import ProjectSettings
from apps.tasks.models import Task
from apps.weeks.rollover import WeekRolloverService
from apps.weeks.services import WeekService


@pytest.mark.django_db
def test_week_rollover_closes_ready_tasks(api_client, ready_column, week_key):
    board = ColumnSettingsService.get_default_board()
    week = WeekService.resolve_week(week_key)
    done_status = TaskStatus.objects.filter(
        board=board,
        slug="done",
        column=ready_column,
    ).first()
    assert done_status is not None
    task = Task.objects.create(
        title="Ready for archive",
        board=board,
        column=ready_column,
        task_status=done_status,
        week=week,
        position=0,
        column_entered_at=timezone.now(),
    )

    settings = ProjectSettings.load()
    settings.week_rollover_iso_year = week.iso_year
    settings.week_rollover_iso_week = week.iso_week
    settings.save(update_fields=["week_rollover_iso_year", "week_rollover_iso_week"])

    next_week = WeekService.next_week(week)
    closed_count = WeekRolloverService.process_for_week(next_week)
    assert closed_count == 1

    task.refresh_from_db()
    assert task.archived_at is not None
    assert task.closed_at is not None


@pytest.mark.django_db
def test_create_task_without_column_uses_backlog(api_client, planned_column):
    response = api_client.post(
        "/api/v1/tasks/",
        {"title": "Default backlog", "task_type": "task"},
        content_type="application/json",
    )
    assert response.status_code == 201
    assert response.json()["column_id"] == planned_column.id
