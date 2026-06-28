from django.db import transaction
from django.utils import timezone

from apps.boards.models import TaskStatus
from apps.jobs.models import JobType
from apps.jobs.services import JobService
from apps.notifications.eligibility import (
    suppress_task_notifications,
    task_accepts_notifications,
)
from apps.notifications.models import (
    CallbackAction,
    TelegramCallbackLog,
)
from apps.tasks.events import EventActor, record_task_event
from apps.tasks.models import ActorType, Task, TaskEventType, TaskSource
from apps.tasks.services import (
    TaskCloseService,
    TaskStatusChangeService,
)


class TelegramActionError(Exception):
    pass


class TelegramActionService:
    @staticmethod
    def handle_callback(
        *,
        callback_query_id: str,
        chat_id: str,
        telegram_user_id: str,
        action: str,
        task_id: int,
        notification_job_id: int | None,
        status_id: int | None = None,
    ) -> dict:
        exists = TelegramCallbackLog.objects.filter(
            callback_query_id=callback_query_id,
        ).exists()
        if exists:
            return {"status": "duplicate"}

        background_job = JobService.create(
            JobType.TELEGRAM_CALLBACK,
            {
                "callback_query_id": callback_query_id,
                "action": action,
                "task_id": task_id,
            },
        )
        JobService.mark_processing(background_job)

        try:
            result = TelegramActionService._execute(
                action=action,
                task_id=task_id,
                status_id=status_id,
                telegram_user_id=telegram_user_id,
            )
        except Exception as exc:
            TelegramCallbackLog.objects.create(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                callback_query_id=callback_query_id,
                task_id=task_id,
                action=action,
                error_message=str(exc),
            )
            JobService.fail(background_job, str(exc))
            raise TelegramActionError(str(exc)) from exc

        TelegramCallbackLog.objects.create(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            callback_query_id=callback_query_id,
            task=Task.objects.filter(pk=task_id).first(),
            action=action,
            payload={
                "notification_job_id": notification_job_id,
                "status_id": status_id,
            },
            processed_at=timezone.now(),
        )
        JobService.succeed(background_job, result)
        return result

    @staticmethod
    @transaction.atomic
    def _execute(
        *,
        action: str,
        task_id: int,
        status_id: int | None,
        telegram_user_id: str,
    ) -> dict:
        task = Task.objects.select_related("column", "board", "task_status").get(
            pk=task_id,
        )
        actor = EventActor(
            ActorType.TELEGRAM,
            telegram_user_id,
            TaskSource.TELEGRAM,
        )

        if action == CallbackAction.TASK_SET_STATUS:
            if status_id is None:
                raise TelegramActionError("Status is required")
            return TelegramActionService._set_status(task, status_id, actor)

        if action == CallbackAction.TASK_DONE:
            return TelegramActionService._mark_done(task, actor)

        if action == CallbackAction.TASK_IN_PROGRESS:
            return TelegramActionService._mark_in_progress(task, actor)

        if action == CallbackAction.TASK_SNOOZE:
            return TelegramActionService._snooze(task, actor)

        if action == CallbackAction.TASK_CANCEL_REMINDERS:
            return TelegramActionService.cancel_reminders(task, actor)

        raise TelegramActionError(f"Unknown action: {action}")

    @staticmethod
    def _mark_done(task: Task, actor: EventActor) -> dict:
        if task.archived_at is not None:
            return {"status": "already_closed"}

        TaskCloseService.close_with_actor(task, actor=actor)
        return {"status": "closed"}

    @staticmethod
    def _set_status(task: Task, target_status_id: int, actor: EventActor) -> dict:
        if task.archived_at is not None:
            return {"status": "already_closed"}

        target_status = TaskStatus.objects.filter(
            board_id=task.board_id,
            id=target_status_id,
        ).first()
        if target_status is None:
            raise TelegramActionError("Status is invalid")

        if target_status.is_terminal and target_status.slug == "done":
            TaskCloseService.close_with_actor(task, actor=actor)
            return {"status": "closed"}

        from apps.boards.task_status_services import TaskStatusService

        source_status = task.task_status
        if source_status is None:
            source_status = TaskStatusService.resolve_column_status(task.column)
        transition = None
        if source_status is not None:
            transition = TaskStatusService.get_transition(
                board=task.board,
                from_status_id=source_status.id,
                to_status_id=target_status.id,
            )
        rules = transition.rules if transition else {}
        required_fields = rules.get("required_fields", [])
        if (
            isinstance(required_fields, list)
            and "description" in required_fields
            and not task.description.strip()
        ):
            task.description = "—"
            task.save(update_fields=["description", "updated_at"])

        TaskStatusChangeService.apply(
            task,
            target_status_id=target_status_id,
            actor=actor,
        )
        task.refresh_from_db()

        if not task_accepts_notifications(task):
            suppress_task_notifications(task)
        else:
            TelegramActionService.schedule_next_reminder_with_event(task, actor)

        return {"status": "status_updated", "status_name": target_status.name}

    @staticmethod
    def _mark_in_progress(task: Task, actor: EventActor) -> dict:
        if task.archived_at is not None:
            return {"status": "already_closed"}

        from apps.boards.task_status_services import TaskStatusService

        process_status = TaskStatus.objects.filter(
            board=task.board,
            slug="process",
        ).first()
        if process_status is None:
            raise TelegramActionError("No in-progress status configured")

        guard = 0
        while task.task_status_id != process_status.id and guard < 5:
            guard += 1
            source_status = task.task_status
            if source_status is None:
                source_status = TaskStatusService.resolve_column_status(task.column)
            targets = TaskStatusService.list_allowed_targets(
                board=task.board,
                from_status=source_status,
            )
            next_status = next(
                (status for status in targets if status.id == process_status.id),
                targets[0] if targets else None,
            )
            if next_status is None:
                raise TelegramActionError("No allowed status transition")
            result = TelegramActionService._set_status(task, next_status.id, actor)
            task.refresh_from_db()
            if result["status"] == "closed":
                return result

        return {"status": "status_updated", "status_name": process_status.name}

    @staticmethod
    def _snooze(task: Task, actor: EventActor) -> dict:
        if task.archived_at is not None:
            return {"status": "already_closed"}
        if not task_accepts_notifications(task):
            return {"status": "reminders_cancelled"}

        TelegramActionService.schedule_next_reminder_with_event(task, actor)
        return {"status": "snoozed"}

    @staticmethod
    def cancel_reminders(task: Task, actor: EventActor) -> dict:
        suppress_task_notifications(task)
        record_task_event(
            task,
            TaskEventType.UPDATED,
            actor=actor,
            payload={"reminder_enabled": False},
        )
        return {"status": "reminders_cancelled"}

    @staticmethod
    def schedule_next_reminder_with_event(task: Task, actor: EventActor) -> None:
        from apps.notifications.scheduling import schedule_next_reminder

        schedule_next_reminder(task)
        next_at = task.next_reminder_at
        record_task_event(
            task,
            TaskEventType.REMINDER_SCHEDULED,
            actor=actor,
            payload={
                "next_reminder_at": next_at.isoformat() if next_at else None,
            },
        )
