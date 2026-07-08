from datetime import time, timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.notifications.actions import TelegramActionService
from apps.notifications.dispatch import NotificationDispatchService
from apps.notifications.models import (
    CallbackAction,
    NotificationJob,
    NotificationReason,
    NotificationStatus,
)
from apps.notifications.planning import ReminderPlanningService
from apps.notifications.scheduling import (
    dedup_bucket,
    interval_for_reason,
    schedule_next_reminder,
)
from apps.tasks.models import Task
from conftest import create_task_via_api


@pytest.mark.django_db
def test_notifications_ec_planning_skips_when_telegram_disabled(stale_task):
    result = ReminderPlanningService.scan()
    assert result["planned"] == 0
    assert result["skipped"] == "telegram_disabled"


@pytest.mark.django_db
def test_notifications_ec_stale_planned_creates_notification(
    telegram_enabled, stale_task
):
    with patch(
        "apps.notifications.tasks.send_telegram_notification.delay"
    ) as mocked_delay:
        result = ReminderPlanningService.scan()
    assert result["planned"] >= 1
    assert NotificationJob.objects.filter(task=stale_task).exists()
    assert mocked_delay.called


@pytest.mark.django_db
def test_notifications_ec_stale_in_progress_uses_bound_column_semantics(
    telegram_enabled,
    stale_task,
    in_progress_column,
):
    from apps.boards.models import TaskStatus

    custom_status = TaskStatus.objects.create(
        board=stale_task.board,
        column=in_progress_column,
        name="Working now",
        slug="working-now",
        color="amber",
        on_flow=True,
        position=999,
    )
    stale_task.column = in_progress_column
    stale_task.task_status = custom_status
    stale_task.column_entered_at = timezone.now() - timedelta(hours=3)
    stale_task.next_reminder_at = None
    stale_task.save(
        update_fields=[
            "column",
            "task_status",
            "column_entered_at",
            "next_reminder_at",
            "updated_at",
        ]
    )

    with patch(
        "apps.notifications.tasks.send_telegram_notification.delay"
    ) as mocked_delay:
        result = ReminderPlanningService.scan()

    assert result["planned"] >= 1
    notification = NotificationJob.objects.filter(task=stale_task).latest("id")
    assert notification.reason == NotificationReason.STALE_IN_PROGRESS
    assert mocked_delay.called


@pytest.mark.django_db
def test_notifications_ec_dedup_prevents_duplicate_notifications(
    telegram_enabled, stale_task
):
    with patch("apps.notifications.tasks.send_telegram_notification.delay"):
        first = ReminderPlanningService.scan()
        second = ReminderPlanningService.scan()
    assert first["planned"] >= 1
    assert second["planned"] == 0


@pytest.mark.django_db
def test_notifications_ec_quiet_hours_skip(telegram_enabled, stale_task):
    telegram_enabled.quiet_hours_start = time(0, 0)
    telegram_enabled.quiet_hours_end = time(23, 59)
    telegram_enabled.save(
        update_fields=["quiet_hours_start", "quiet_hours_end", "updated_at"]
    )
    result = ReminderPlanningService.scan()
    assert result["planned"] == 0
    assert result["skipped"] == "quiet_hours"


@pytest.mark.django_db
def test_notifications_ec_dispatch_send_uses_mocked_deliver(
    telegram_enabled, stale_task
):
    with patch("apps.notifications.tasks.send_telegram_notification.delay"):
        ReminderPlanningService.scan()
    notification = NotificationJob.objects.filter(task=stale_task).latest("id")
    with patch.object(NotificationDispatchService, "_deliver", return_value="42"):
        result = NotificationDispatchService.send(
            notification.id, notification.background_job_id
        )
    notification.refresh_from_db()
    assert result["message_id"] == "42"
    assert notification.status == NotificationStatus.SUCCEEDED


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        pytest.param(
            CallbackAction.TASK_DONE, "closed", id="ec_callback_done_closes_task"
        ),
        pytest.param(
            CallbackAction.TASK_IN_PROGRESS,
            "status_updated",
            id="ec_callback_in_progress_moves_or_reschedules",
        ),
        pytest.param(
            CallbackAction.TASK_SNOOZE, "snoozed", id="ec_callback_snooze_reschedules"
        ),
        pytest.param(
            CallbackAction.TASK_CANCEL_REMINDERS,
            "reminders_cancelled",
            id="ec_callback_cancel_disables_reminders",
        ),
    ],
)
def test_notifications_ec_telegram_action_callbacks(
    action, expected_status, api_client, planned_column
):
    created = create_task_via_api(
        api_client, title=f"TG {action}", column_id=planned_column.id
    )
    task_id = created.json()["id"]
    with patch(
        "apps.notifications.actions.schedule_next_reminder_with_event", create=True
    ):
        result = TelegramActionService.handle_callback(
            callback_query_id=f"cb-{action}",
            chat_id="123",
            telegram_user_id="321",
            action=action,
            task_id=task_id,
            notification_job_id=None,
        )
    assert result["status"] == expected_status


@pytest.mark.django_db
def test_notifications_ec_telegram_action_duplicate_callback_idempotent(
    api_client, planned_column
):
    created = create_task_via_api(
        api_client, title="TG duplicate", column_id=planned_column.id
    )
    task_id = created.json()["id"]
    first = TelegramActionService.handle_callback(
        callback_query_id="cb-dup-1",
        chat_id="123",
        telegram_user_id="321",
        action=CallbackAction.TASK_SNOOZE,
        task_id=task_id,
        notification_job_id=None,
    )
    second = TelegramActionService.handle_callback(
        callback_query_id="cb-dup-1",
        chat_id="123",
        telegram_user_id="321",
        action=CallbackAction.TASK_SNOOZE,
        task_id=task_id,
        notification_job_id=None,
    )
    assert first["status"] in {"snoozed", "already_closed"}
    assert second["status"] == "duplicate"


@pytest.mark.django_db
def test_notifications_ec_scheduling_dedup_bucket_and_intervals(
    telegram_enabled, stale_task
):
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    assert dedup_bucket(now, 30) == dedup_bucket(now + timedelta(minutes=1), 30)
    assert (
        interval_for_reason(NotificationReason.REMINDER, stale_task, telegram_enabled)
        > 0
    )
    assert (
        interval_for_reason(NotificationReason.OVERDUE, stale_task, telegram_enabled)
        > 0
    )
    assert (
        interval_for_reason(
            NotificationReason.STALE_PLANNED, stale_task, telegram_enabled
        )
        > 0
    )
    assert (
        interval_for_reason(
            NotificationReason.STALE_IN_PROGRESS, stale_task, telegram_enabled
        )
        > 0
    )
    assert (
        interval_for_reason(NotificationReason.MANUAL, stale_task, telegram_enabled) > 0
    )


@pytest.mark.django_db
def test_notifications_ec_schedule_next_reminder_disabled_clears_next_at(stale_task):
    stale_task.reminder_enabled = False
    stale_task.next_reminder_at = timezone.now() + timedelta(hours=2)
    stale_task.save(
        update_fields=["reminder_enabled", "next_reminder_at", "updated_at"]
    )
    schedule_next_reminder(stale_task)
    stale_task.refresh_from_db()
    assert stale_task.next_reminder_at is None


@pytest.mark.django_db
def test_notifications_ec_api_notify_snooze_cancel(
    api_client, telegram_enabled, planned_column
):
    created = create_task_via_api(
        api_client, title="Notify API", column_id=planned_column.id
    )
    task_id = created.json()["id"]
    with patch("apps.notifications.tasks.send_telegram_notification.delay"):
        notify = api_client.post(reverse("task-notify", args=[task_id]))
    assert notify.status_code == 201
    snooze = api_client.post(
        reverse("task-reminder-snooze", args=[task_id]),
        {"minutes": 15},
        content_type="application/json",
    )
    assert snooze.status_code == 200
    cancelled = api_client.post(reverse("task-reminder-cancel", args=[task_id]))
    assert cancelled.status_code == 200
    task = Task.objects.get(pk=task_id)
    assert task.reminder_enabled is False


@pytest.mark.django_db
def test_notifications_ec_list_endpoint_returns_jobs(
    session_client, telegram_enabled, stale_task
):
    with patch("apps.notifications.tasks.send_telegram_notification.delay"):
        ReminderPlanningService.scan()
    response = session_client.get(reverse("notification-list"))
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 1
    assert payload[0]["task_id"] == stale_task.id


@pytest.mark.django_db
def test_notifications_ec_list_filters_by_status(
    session_client, telegram_enabled, stale_task
):
    with patch("apps.notifications.tasks.send_telegram_notification.delay"):
        ReminderPlanningService.scan()
    notification = NotificationJob.objects.filter(task=stale_task).latest("id")
    response = session_client.get(
        reverse("notification-list"),
        {"status": notification.status},
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert notification.id in ids


@pytest.mark.django_db
def test_notifications_ec_list_filters_by_task_id(
    session_client, telegram_enabled, stale_task
):
    with patch("apps.notifications.tasks.send_telegram_notification.delay"):
        ReminderPlanningService.scan()
    notification = NotificationJob.objects.filter(task=stale_task).latest("id")
    response = session_client.get(
        reverse("notification-list"),
        {"task_id": stale_task.id},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert all(item["task_id"] == stale_task.id for item in payload)
    assert notification.id in {item["id"] for item in payload}


@pytest.mark.django_db
def test_notifications_ec_skips_done_and_cancel_statuses(
    telegram_enabled, api_client, planned_column, ready_column
):
    from apps.boards.models import TaskStatus

    for slug in ("done", "cancel"):
        created = create_task_via_api(
            api_client,
            title=f"Terminal {slug}",
            column_id=planned_column.id,
        )
        task = Task.objects.get(pk=created.json()["id"])
        status = TaskStatus.objects.get(board=task.board, slug=slug)
        task.task_status = status
        task.column = ready_column
        task.reminder_enabled = True
        task.next_reminder_at = timezone.now() - timedelta(minutes=5)
        task.save(
            update_fields=[
                "task_status",
                "column",
                "reminder_enabled",
                "next_reminder_at",
                "updated_at",
            ],
        )

    with patch(
        "apps.notifications.tasks.send_telegram_notification.delay",
    ) as mocked_delay:
        result = ReminderPlanningService.scan()

    assert result["planned"] == 0
    assert mocked_delay.call_count == 0
