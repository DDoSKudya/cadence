from django.db import transaction
from django.utils import timezone

from apps.boards.models import BoardColumn, SystemType, TaskStatus
from apps.jobs.models import JobType
from apps.jobs.services import JobService
from apps.notifications.models import (
    CallbackAction,
    NotificationJob,
    NotificationStatus,
    TelegramCallbackLog,
)
from apps.tasks.events import EventActor, record_task_event
from apps.tasks.models import ActorType, Task, TaskEventType, TaskSource
from apps.tasks.services import (
    TaskCloseService,
    TaskCreationService,
    TaskMoveService,
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
            payload={"notification_job_id": notification_job_id},
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
        telegram_user_id: str,
    ) -> dict:
        task = Task.objects.select_related("column", "board").get(pk=task_id)
        actor = EventActor(
            ActorType.TELEGRAM,
            telegram_user_id,
            TaskSource.TELEGRAM,
        )

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
    def _mark_in_progress(task: Task, actor: EventActor) -> dict:
        if task.archived_at is not None:
            return {"status": "already_closed"}

        process_status = TaskStatus.objects.filter(
            board=task.board,
            slug="process",
        ).first()
        if process_status is None:
            column = BoardColumn.objects.filter(
                board=task.board,
                system_type=SystemType.IN_PROGRESS,
                is_active=True,
            ).first()
            if column is not None and task.column_id != column.id:
                TaskMoveService.move_with_actor(
                    task,
                    target_column=column,
                    target_position=TaskCreationService._next_position(column),
                    actor=actor,
                )
        else:
            source_status = task.task_status
            if source_status is not None and source_status.slug == "open":
                ready_status = TaskStatus.objects.filter(
                    board=task.board,
                    slug="ready_on_develop",
                ).first()
                if ready_status is not None:
                    if not task.description.strip():
                        task.description = "—"
                        task.save(update_fields=["description", "updated_at"])
                    TaskStatusChangeService.apply(
                        task,
                        target_status_id=ready_status.id,
                        actor=actor,
                    )
                    task.refresh_from_db()
            TaskStatusChangeService.apply(
                task,
                target_status_id=process_status.id,
                actor=actor,
            )

        TelegramActionService.schedule_next_reminder_with_event(task, actor)
        return {"status": "in_progress"}

    @staticmethod
    def _snooze(task: Task, actor: EventActor) -> dict:
        if task.archived_at is not None:
            return {"status": "already_closed"}

        TelegramActionService.schedule_next_reminder_with_event(task, actor)
        return {"status": "snoozed"}

    @staticmethod
    def cancel_reminders(task: Task, actor: EventActor) -> dict:
        task.reminder_enabled = False
        task.next_reminder_at = None
        task.save(update_fields=["reminder_enabled", "next_reminder_at", "updated_at"])
        NotificationJob.objects.filter(
            task=task,
            status=NotificationStatus.PENDING,
        ).update(status=NotificationStatus.CANCELLED)
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
