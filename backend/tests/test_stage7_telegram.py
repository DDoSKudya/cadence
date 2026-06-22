from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.boards.models import BoardColumn, SystemType
from apps.boards.services import ColumnSettingsService
from apps.core.models import ApiKey, ProjectSettings
from apps.notifications.actions import TelegramActionService
from apps.notifications.dispatch import NotificationDispatchService
from apps.notifications.models import (
    CallbackAction,
    NotificationJob,
    NotificationReason,
    NotificationStatus,
    TelegramCallbackLog,
)
from apps.notifications.planning import ReminderPlanningService
from apps.tasks.models import Task, TaskEvent, TaskEventType


@pytest.fixture
def api_client_auth(client):
    api_key, raw_key = ApiKey.issue("telegram-tests")
    client.defaults["HTTP_AUTHORIZATION"] = f"Api-Key {raw_key}"
    return client, api_key


@pytest.fixture
def telegram_settings(settings):
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    project_settings = ProjectSettings.load()
    project_settings.telegram_enabled = True
    project_settings.telegram_bot_token = "test-token"
    project_settings.telegram_recipients = [
        {"chat_id": "12345", "label": "Test user", "kind": "user"},
    ]
    project_settings.stale_in_progress_minutes = 60
    project_settings.stale_planned_minutes = 120
    project_settings.default_reminder_interval_minutes = 30
    project_settings.save()
    return project_settings


@pytest.fixture
def planned_column():
    board = ColumnSettingsService.get_default_board()
    return BoardColumn.objects.get(board=board, system_type=SystemType.PLANNED)


@pytest.fixture
def in_progress_column():
    board = ColumnSettingsService.get_default_board()
    return BoardColumn.objects.get(board=board, system_type=SystemType.IN_PROGRESS)


@pytest.fixture
def active_task(planned_column):
    now = timezone.now()
    return Task.objects.create(
        title="Stale planned task",
        board=planned_column.board,
        column=planned_column,
        position=0,
        column_entered_at=now - timedelta(hours=3),
        reminder_enabled=True,
    )


@pytest.mark.django_db
def test_reminder_planning_creates_notification_for_stale_task(
    telegram_settings,
    active_task,
):
    with patch("apps.notifications.tasks.send_telegram_notification.delay"):
        result = ReminderPlanningService.scan()

    assert result["planned"] == 1
    notification = NotificationJob.objects.get(task=active_task)
    assert notification.status == NotificationStatus.PENDING
    assert notification.reason == NotificationReason.STALE_PLANNED
    assert notification.telegram_chat_id == "12345"


@pytest.mark.django_db
def test_reminder_planning_deduplicates_same_hour(telegram_settings, active_task):
    with patch("apps.notifications.tasks.send_telegram_notification.delay"):
        ReminderPlanningService.scan()
        result = ReminderPlanningService.scan()

    assert result["planned"] == 0
    assert NotificationJob.objects.filter(task=active_task).count() == 1


@pytest.mark.django_db
def test_reminder_planning_skips_when_disabled(active_task):
    settings = ProjectSettings.load()
    settings.telegram_enabled = False
    settings.save()

    result = ReminderPlanningService.scan()

    assert result["skipped"] == "telegram_disabled"
    assert NotificationJob.objects.count() == 0


@pytest.mark.django_db
@patch(
    "apps.notifications.dispatch.NotificationDispatchService._deliver",
    return_value="42",
)
def test_notification_dispatch_marks_job_succeeded(
    _deliver,
    telegram_settings,
    active_task,
):
    notification = NotificationJob.objects.create(
        task=active_task,
        telegram_chat_id="12345",
        message_text="Test",
        reason=NotificationReason.MANUAL,
        scheduled_at=timezone.now(),
        dedup_key="manual:test:1",
        status=NotificationStatus.PENDING,
    )

    result = NotificationDispatchService.send(notification.id)

    notification.refresh_from_db()
    active_task.refresh_from_db()
    assert result["message_id"] == "42"
    assert notification.status == NotificationStatus.SUCCEEDED
    assert notification.message_id == "42"
    assert active_task.last_notified_at is not None
    assert TaskEvent.objects.filter(
        task=active_task,
        event_type=TaskEventType.NOTIFICATION_SENT,
    ).exists()


@pytest.mark.django_db
def test_telegram_callback_done_closes_task(
    telegram_settings,
    active_task,
    api_client_auth,
):
    client, _api_key = api_client_auth

    result = TelegramActionService.handle_callback(
        callback_query_id="cb-1",
        chat_id="12345",
        telegram_user_id="999",
        action=CallbackAction.TASK_DONE,
        task_id=active_task.id,
        notification_job_id=None,
    )

    active_task.refresh_from_db()
    assert result["status"] == "closed"
    assert active_task.archived_at is not None
    assert TelegramCallbackLog.objects.filter(callback_query_id="cb-1").exists()
    assert TaskEvent.objects.filter(
        task=active_task,
        event_type=TaskEventType.CLOSED,
    ).exists()


@pytest.mark.django_db
def test_telegram_callback_is_idempotent(telegram_settings, active_task):
    TelegramActionService.handle_callback(
        callback_query_id="cb-dup",
        chat_id="12345",
        telegram_user_id="999",
        action=CallbackAction.TASK_SNOOZE,
        task_id=active_task.id,
        notification_job_id=None,
    )

    result = TelegramActionService.handle_callback(
        callback_query_id="cb-dup",
        chat_id="12345",
        telegram_user_id="999",
        action=CallbackAction.TASK_SNOOZE,
        task_id=active_task.id,
        notification_job_id=None,
    )

    assert result["status"] == "duplicate"
    assert TelegramCallbackLog.objects.filter(callback_query_id="cb-dup").count() == 1


@pytest.mark.django_db
def test_telegram_in_progress_schedules_next_reminder(
    telegram_settings,
    active_task,
):
    TelegramActionService.handle_callback(
        callback_query_id="cb-progress",
        chat_id="12345",
        telegram_user_id="999",
        action=CallbackAction.TASK_IN_PROGRESS,
        task_id=active_task.id,
        notification_job_id=None,
    )

    active_task.refresh_from_db()
    assert active_task.next_reminder_at is not None
    assert TaskEvent.objects.filter(
        task=active_task,
        event_type=TaskEventType.REMINDER_SCHEDULED,
    ).exists()


@pytest.mark.django_db
def test_manual_notify_api(telegram_settings, active_task, api_client_auth):
    client, _api_key = api_client_auth

    with patch("apps.notifications.tasks.send_telegram_notification.delay"):
        response = client.post(reverse("task-notify", args=[active_task.id]))

    assert response.status_code == 201
    assert NotificationJob.objects.filter(
        task=active_task,
        reason=NotificationReason.MANUAL,
    ).exists()


@pytest.mark.django_db
def test_notification_dispatch_reschedules_interval_reminder(
    telegram_settings,
    active_task,
):
    active_task.next_reminder_at = timezone.now() - timedelta(minutes=5)
    active_task.save(update_fields=["next_reminder_at"])

    notification = NotificationJob.objects.create(
        task=active_task,
        telegram_chat_id="12345",
        message_text="Reminder",
        reason=NotificationReason.REMINDER,
        scheduled_at=timezone.now(),
        dedup_key="reminder:test:1",
        status=NotificationStatus.PENDING,
    )

    with patch(
        "apps.notifications.dispatch.NotificationDispatchService._deliver",
        return_value="99",
    ):
        NotificationDispatchService.send(notification.id)

    active_task.refresh_from_db()
    assert active_task.next_reminder_at is not None
    assert active_task.next_reminder_at > timezone.now()


@pytest.mark.django_db
def test_notification_dispatch_resets_stale_timer(
    telegram_settings,
    active_task,
):
    entered_at = timezone.now() - timedelta(hours=5)
    active_task.column_entered_at = entered_at
    active_task.save(update_fields=["column_entered_at"])

    notification = NotificationJob.objects.create(
        task=active_task,
        telegram_chat_id="12345",
        message_text="Stale",
        reason=NotificationReason.STALE_PLANNED,
        scheduled_at=timezone.now(),
        dedup_key="stale:test:1",
        status=NotificationStatus.PENDING,
    )

    with patch(
        "apps.notifications.dispatch.NotificationDispatchService._deliver",
        return_value="99",
    ):
        NotificationDispatchService.send(notification.id)

    active_task.refresh_from_db()
    assert active_task.column_entered_at > entered_at


@pytest.mark.django_db
def test_settings_interval_refresh_updates_tasks(
    client,
    django_user_model,
    telegram_settings,
):
    user = django_user_model.objects.create_user(username="admin2", password="admin")
    client.force_login(user)

    board = ColumnSettingsService.get_default_board()
    backlog = BoardColumn.objects.get(board=board, system_type=SystemType.BACKLOG)
    task = Task.objects.create(
        title="Reminder task",
        board=board,
        column=backlog,
        position=0,
        column_entered_at=timezone.now(),
        reminder_enabled=True,
        next_reminder_at=timezone.now() + timedelta(days=1),
    )

    response = client.patch(
        reverse("settings"),
        {"default_reminder_interval_minutes": 15},
        content_type="application/json",
    )
    assert response.status_code == 200

    task.refresh_from_db()
    assert task.next_reminder_at is not None
    delta = task.next_reminder_at - timezone.now()
    assert delta.total_seconds() < 20 * 60


@pytest.mark.django_db
def test_scan_reminders_task(telegram_settings, active_task):
    from apps.notifications.tasks import scan_reminders

    with patch("apps.notifications.tasks.send_telegram_notification.delay"):
        result = scan_reminders.run()

    assert result["planned"] == 1
