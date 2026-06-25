from dataclasses import dataclass
from datetime import datetime
from typing import NotRequired, TypedDict

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from apps.boards.models import Board, BoardColumn, SystemType, TaskStatus
from apps.boards.services import ColumnSettingsService, ColumnWorkflowService
from apps.boards.task_status_services import TaskStatusService
from apps.core.tag_services import TagService
from apps.notifications.scheduling import schedule_next_reminder
from apps.tasks.events import (
    EventActor,
    record_request_event,
    record_task_event,
    resolve_request_context,
)
from apps.tasks.models import Task, TaskEvent, TaskEventType
from apps.weeks.models import Week
from apps.weeks.services import WeekService


class TaskCreateData(TypedDict):
    title: str
    description: NotRequired[str]
    column_id: NotRequired[int]
    week: NotRequired[str | None]
    priority: NotRequired[str]
    tags: NotRequired[list[str]]
    due_at: NotRequired[datetime | None]
    evidence_url: NotRequired[str]
    reminder_enabled: NotRequired[bool]


@dataclass(frozen=True)
class TaskCreateInput:
    board: Board
    title: str
    column: BoardColumn
    actor: EventActor
    description: str = ""
    week: Week | None = None
    priority: str = "normal"
    tag_slugs: list[str] | None = None
    due_at: datetime | None = None
    evidence_url: str = ""
    reminder_enabled: bool = True
    reminder_interval_minutes: int | None = None
    created_by: User | None = None
    external_ref: str = ""


@dataclass(frozen=True)
class TaskUpdateInput:
    request: Request
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    week: Week | None = None
    week_provided: bool = False
    clear_week: bool = False
    due_at: datetime | None = None
    clear_due_at: bool = False
    evidence_url: str | None = None
    reminder_enabled: bool | None = None
    reminder_interval_minutes: int | None = None
    clear_reminder_interval: bool = False
    tag_slugs: list[str] | None = None
    task_status_id: int | None = None
    task_status_provided: bool = False


class TaskCreationService:
    @staticmethod
    @transaction.atomic
    def create(data: TaskCreateInput) -> Task:
        if data.column.board_id != data.board.id or not data.column.is_active:
            raise ValidationError("Column is invalid.")

        position = TaskCreationService._next_position(data.column)
        now = timezone.now()
        initial_status = TaskStatusService.get_initial_status(data.board)
        target_column = data.column
        if initial_status is not None:
            task_status: TaskStatus | None = initial_status
            status_column = initial_status.column
            if status_column is not None and status_column.is_active:
                target_column = status_column
            position = TaskCreationService._next_position(target_column)
        else:
            task_status = TaskStatusService.resolve_column_status(data.column)
        task = Task.objects.create(
            title=data.title.strip(),
            description=data.description,
            board=data.board,
            column=target_column,
            task_status=task_status,
            week=data.week,
            position=position,
            priority=data.priority,
            column_entered_at=now,
            due_at=data.due_at,
            source=data.actor.source,
            evidence_url=data.evidence_url,
            reminder_enabled=data.reminder_enabled,
            reminder_interval_minutes=data.reminder_interval_minutes,
            created_by=data.created_by,
            external_ref=data.external_ref,
        )
        schedule_next_reminder(task)
        TaskCreationService._set_tags(task, data.tag_slugs or [])
        record_task_event(
            task,
            TaskEventType.CREATED,
            actor=data.actor,
            payload={
                "column_id": target_column.id,
                "task_status_id": task_status.id if task_status else None,
                "week_id": data.week.id if data.week else None,
            },
        )
        return task

    @staticmethod
    def _next_position(column: BoardColumn) -> int:
        max_position = Task.objects.filter(
            column=column,
            archived_at__isnull=True,
        ).aggregate(max_position=Max("position"))["max_position"]
        return 0 if max_position is None else max_position + 1

    @staticmethod
    def _set_tags(task: Task, tag_slugs: list[str]) -> None:
        if not tag_slugs:
            task.tags.clear()
            return

        board = task.column.board
        tags = TagService.resolve_slugs_for_board(board=board, tag_slugs=tag_slugs)
        task.tags.set(tags)


class TaskUpdateService:
    @staticmethod
    @transaction.atomic
    def update(task: Task, data: TaskUpdateInput) -> Task:
        if task.archived_at is not None:
            raise ValidationError("Archived task cannot be updated.")

        fields = TaskUpdateService._apply_fields(task, data)

        if fields:
            fields.append("updated_at")
            task.save(update_fields=fields)

        if (
            data.reminder_enabled is not None
            or data.reminder_interval_minutes is not None
        ):
            schedule_next_reminder(task)

        if data.tag_slugs is not None:
            TaskCreationService._set_tags(task, data.tag_slugs)

        status_changed = False
        if data.task_status_provided:
            actor = resolve_request_context(data.request)
            task = TaskStatusChangeService.apply(
                task,
                target_status_id=data.task_status_id,
                actor=actor,
            )
            status_changed = True

        if data.tag_slugs is not None:
            TaskCreationService._set_tags(task, data.tag_slugs)

        if fields or data.tag_slugs is not None:
            record_request_event(task, TaskEventType.UPDATED, data.request)
        elif not status_changed and data.task_status_provided:
            pass

        return task

    @staticmethod
    def _apply_fields(task: Task, data: TaskUpdateInput) -> list[str]:
        fields: list[str] = []
        TaskUpdateService._apply_basic_fields(task, data, fields)
        TaskUpdateService._apply_schedule_fields(task, data, fields)
        return fields

    @staticmethod
    def _apply_basic_fields(
        task: Task,
        data: TaskUpdateInput,
        fields: list[str],
    ) -> None:
        if data.title is not None:
            task.title = data.title.strip()
            fields.append("title")
        if data.description is not None:
            task.description = data.description
            fields.append("description")
        if data.priority is not None:
            task.priority = data.priority
            fields.append("priority")
        if data.clear_week:
            task.week = None
            fields.append("week")
        elif data.week_provided:
            task.week = data.week
            fields.append("week")
        if data.clear_due_at:
            task.due_at = None
            fields.append("due_at")
        elif data.due_at is not None:
            task.due_at = data.due_at
            fields.append("due_at")
        if data.evidence_url is not None:
            task.evidence_url = data.evidence_url
            fields.append("evidence_url")

    @staticmethod
    def _apply_schedule_fields(
        task: Task,
        data: TaskUpdateInput,
        fields: list[str],
    ) -> None:
        if data.reminder_enabled is not None:
            task.reminder_enabled = data.reminder_enabled
            fields.append("reminder_enabled")
        if data.clear_reminder_interval:
            task.reminder_interval_minutes = None
            fields.append("reminder_interval_minutes")
        elif data.reminder_interval_minutes is not None:
            task.reminder_interval_minutes = data.reminder_interval_minutes
            fields.append("reminder_interval_minutes")


class TaskStatusChangeService:
    @staticmethod
    @transaction.atomic
    def apply(
        task: Task,
        *,
        target_status_id: int | None,
        actor: EventActor,
    ) -> Task:
        if task.archived_at is not None:
            raise ValidationError("Archived task cannot be updated.")

        if target_status_id is None:
            raise ValidationError("Task status is invalid.")

        target_status = (
            TaskStatus.objects.filter(board_id=task.board_id, id=target_status_id)
            .select_related("column")
            .first()
        )
        if target_status is None:
            raise ValidationError("Task status is invalid.")

        source_status = task.task_status
        if source_status is None:
            source_status = TaskStatusService.resolve_column_status(task.column)

        if source_status is not None and source_status.id == target_status.id:
            return task

        TaskStatusService.validate_status_change(
            task=task,
            from_status=source_status,
            to_status=target_status,
        )

        source_column = task.column
        if target_status.column_id and target_status.column_id != task.column_id:
            target_column = target_status.column
            if target_column is None or not target_column.is_active:
                raise ValidationError("Target column is invalid.")
            column_move_ok = ColumnWorkflowService.is_move_allowed(
                board=task.board,
                from_column_id=source_column.id,
                to_column_id=target_column.id,
            )
            status_move_ok = TaskStatusService.is_transition_allowed(
                board=task.board,
                from_status_id=source_status.id if source_status else None,
                to_status_id=target_status.id,
            )
            if not column_move_ok and not status_move_ok:
                raise ValidationError(
                    {
                        "detail": "Transition from this column is not allowed.",
                        "code": "transition_not_allowed",
                    },
                )
            target_position = TaskCreationService._next_position(target_column)
            TaskMoveService._move_between_columns(
                task,
                source_column=source_column,
                target_column=target_column,
                target_position=target_position,
                target_status=target_status,
            )
            record_task_event(
                task,
                TaskEventType.MOVED,
                actor=actor,
                payload={
                    "from_column_id": source_column.id,
                    "to_column_id": task.column_id,
                    "from_system_type": source_column.system_type,
                    "to_system_type": task.column.system_type,
                    "from_task_status_id": source_status.id if source_status else None,
                    "to_task_status_id": task.task_status_id,
                    "position": task.position,
                },
            )
        else:
            task.task_status = target_status
            task.save(update_fields=["task_status_id", "updated_at"])

        record_task_event(
            task,
            TaskEventType.UPDATED,
            actor=actor,
            payload={
                "from_task_status_id": source_status.id if source_status else None,
                "to_task_status_id": task.task_status_id,
            },
        )
        return task


class TaskMoveService:
    @staticmethod
    @transaction.atomic
    def move(
        task: Task,
        *,
        target_column: BoardColumn,
        target_position: int,
        request: Request,
    ) -> Task:
        return TaskMoveService.move_with_actor(
            task,
            target_column=target_column,
            target_position=target_position,
            actor=resolve_request_context(request),
        )

    @staticmethod
    @transaction.atomic
    def move_with_actor(
        task: Task,
        *,
        target_column: BoardColumn,
        target_position: int,
        actor: EventActor,
    ) -> Task:
        if task.archived_at is not None:
            raise ValidationError("Archived task cannot be moved.")

        if target_column.board_id != task.board_id or not target_column.is_active:
            raise ValidationError("Target column is invalid.")

        if target_position < 0:
            raise ValidationError("Target position must be non-negative.")

        source_column = task.column
        source_status = task.task_status
        target_status = None
        effective_target_column = target_column

        if source_status and source_status.is_terminal:
            raise ValidationError(
                "Task in a terminal status cannot be moved.",
                code="status_terminal",
            )

        if source_column.id == target_column.id:
            TaskMoveService._reorder_within_column(task, target_position)
        else:
            if not ColumnWorkflowService.is_move_allowed(
                board=task.board,
                from_column_id=source_column.id,
                to_column_id=target_column.id,
            ) and not TaskStatusService.can_move_between_columns_via_status(
                task=task,
                source_column=source_column,
                target_column=target_column,
            ):
                raise ValidationError(
                    {
                        "detail": "Transition from this column is not allowed.",
                        "code": "transition_not_allowed",
                    },
                )
            if source_status is None:
                source_status = TaskStatusService.resolve_column_status(source_column)

            target_status = TaskStatusService.resolve_target_status_for_column(
                task=task,
                source_status=source_status,
                source_column=source_column,
                target_column=target_column,
            )
            if target_status is None:
                raise ValidationError(
                    {
                        "detail": (
                            "Task cannot be moved to this column "
                            "with the current status."
                        ),
                        "code": "status_column_move_not_allowed",
                        "from_status": source_status.name if source_status else "",
                        "from_status_slug": source_status.slug if source_status else "",
                        "to_column": target_column.name,
                        "to_column_type": target_column.system_type,
                    },
                )

            TaskStatusService.validate_status_change(
                task=task,
                from_status=source_status,
                to_status=target_status,
            )

            if target_status.column_id:
                status_column = target_status.column
                if status_column is not None:
                    effective_target_column = status_column

            TaskMoveService._move_between_columns(
                task,
                source_column=source_column,
                target_column=effective_target_column,
                target_position=target_position,
                target_status=target_status,
            )

        record_task_event(
            task,
            TaskEventType.MOVED,
            actor=actor,
            payload={
                "from_column_id": source_column.id,
                "to_column_id": task.column_id,
                "from_system_type": source_column.system_type,
                "to_system_type": task.column.system_type,
                "from_task_status_id": source_status.id if source_status else None,
                "to_task_status_id": task.task_status_id,
                "position": task.position,
            },
        )
        return task

    @staticmethod
    def _lock_column_tasks(column: BoardColumn) -> list[Task]:
        return list(
            Task.objects.select_for_update()
            .filter(column=column, archived_at__isnull=True)
            .order_by("position"),
        )

    @staticmethod
    def _save_positions(
        tasks: list[Task],
        *,
        moved_task: Task | None = None,
        include_task_status: bool = False,
    ) -> None:
        for index, item in enumerate(tasks):
            item.position = index
            update_fields = ["position", "updated_at"]
            if moved_task is not None and item.pk == moved_task.pk:
                update_fields.extend(["column_id", "column_entered_at"])
                if include_task_status:
                    update_fields.append("task_status_id")
            item.save(update_fields=update_fields)

    @staticmethod
    def _reorder_within_column(task: Task, target_position: int) -> None:
        tasks = TaskMoveService._lock_column_tasks(task.column)
        tasks = [item for item in tasks if item.id != task.id]
        target_position = min(target_position, len(tasks))
        tasks.insert(target_position, task)
        TaskMoveService._save_positions(tasks)

    @staticmethod
    def _move_between_columns(
        task: Task,
        *,
        source_column: BoardColumn,
        target_column: BoardColumn,
        target_position: int,
        target_status=None,
    ) -> None:
        source_tasks = TaskMoveService._lock_column_tasks(source_column)
        target_tasks = TaskMoveService._lock_column_tasks(target_column)

        source_tasks = [item for item in source_tasks if item.id != task.id]
        TaskMoveService._save_positions(source_tasks)

        target_position = min(target_position, len(target_tasks))
        task.column = target_column
        task.column_entered_at = timezone.now()
        if target_status is not None:
            task.task_status = target_status
        target_tasks.insert(target_position, task)
        TaskMoveService._save_positions(
            target_tasks,
            moved_task=task,
            include_task_status=target_status is not None,
        )


class TaskCloseService:
    @staticmethod
    @transaction.atomic
    def close(
        task: Task,
        *,
        completion_note: str = "",
        evidence_url: str | None = None,
        request: Request,
    ) -> Task:
        return TaskCloseService.close_with_actor(
            task,
            completion_note=completion_note,
            evidence_url=evidence_url,
            actor=resolve_request_context(request),
        )

    @staticmethod
    @transaction.atomic
    def close_with_actor(
        task: Task,
        *,
        completion_note: str = "",
        evidence_url: str | None = None,
        actor: EventActor,
    ) -> Task:
        if task.archived_at is not None:
            raise ValidationError("Task is already closed.")

        done_column = BoardColumn.objects.filter(
            board=task.board,
            system_type=SystemType.DONE,
            is_active=True,
        ).first()

        from_column_id = task.column_id
        if done_column is not None and task.column_id != done_column.id:
            TaskMoveService.move_with_actor(
                task,
                target_column=done_column,
                target_position=TaskCreationService._next_position(done_column),
                actor=actor,
            )

        now = timezone.now()
        task.completion_note = completion_note
        task.closed_at = now
        task.archived_at = now
        update_fields = ["completion_note", "closed_at", "archived_at", "updated_at"]
        if evidence_url is not None:
            task.evidence_url = evidence_url
            update_fields.append("evidence_url")
        task.save(update_fields=update_fields)

        TaskCloseService._cancel_pending_notifications(task.id)
        record_task_event(
            task,
            TaskEventType.CLOSED,
            actor=actor,
            payload={"from_column_id": from_column_id},
        )
        return task

    @staticmethod
    def _cancel_pending_notifications(task_id: int) -> None:
        from django.apps import apps as django_apps

        if not django_apps.is_installed("apps.notifications"):
            return

        notification_job = django_apps.get_model("notifications", "NotificationJob")
        from apps.notifications.models import NotificationStatus

        notification_job.objects.filter(
            task_id=task_id,
            status=NotificationStatus.PENDING,
        ).update(status=NotificationStatus.CANCELLED)


class TaskReopenService:
    @staticmethod
    @transaction.atomic
    def reopen(task: Task, *, request: Request) -> Task:
        if task.archived_at is None:
            raise ValidationError("Task is not archived.")

        target_column = TaskReopenService._resolve_target_column(task)
        task.closed_at = None
        task.archived_at = None
        task.save(update_fields=["closed_at", "archived_at", "updated_at"])

        TaskMoveService.move(
            task,
            target_column=target_column,
            target_position=TaskCreationService._next_position(target_column),
            request=request,
        )
        record_request_event(
            task,
            TaskEventType.REOPENED,
            request,
            payload={"to_column_id": target_column.id},
        )
        return task

    @staticmethod
    def _resolve_target_column(task: Task) -> BoardColumn:
        last_closed = (
            TaskEvent.objects.filter(task=task, event_type=TaskEventType.CLOSED)
            .order_by("-created_at")
            .first()
        )
        if last_closed is not None:
            from_column_id = last_closed.payload.get("from_column_id")
            if from_column_id is not None:
                column = (
                    BoardColumn.objects.filter(
                        id=from_column_id,
                        board=task.board,
                        is_active=True,
                    )
                    .exclude(system_type=SystemType.DONE)
                    .first()
                )
                if column is not None:
                    return column

        planned = BoardColumn.objects.filter(
            board=task.board,
            system_type=SystemType.PLANNED,
            is_active=True,
        ).first()
        if planned is not None:
            return planned

        backlog = BoardColumn.objects.filter(
            board=task.board,
            system_type=SystemType.BACKLOG,
            is_active=True,
        ).first()
        if backlog is not None:
            return backlog

        fallback = (
            BoardColumn.objects.filter(board=task.board, is_active=True)
            .exclude(system_type=SystemType.DONE)
            .order_by("position")
            .first()
        )
        if fallback is None:
            raise ValidationError("No active column available for reopen.")

        return fallback


def create_task_from_request(request: Request, data: TaskCreateData) -> Task:
    board = ColumnSettingsService.get_default_board()
    column_id = data.get("column_id")
    if column_id is None:
        column = BoardColumn.objects.filter(
            board=board,
            system_type=SystemType.BACKLOG,
            is_active=True,
        ).first()
    else:
        column = BoardColumn.objects.filter(
            id=column_id,
            board=board,
            is_active=True,
        ).first()

    if column is None:
        raise ValidationError("Column is invalid.")

    week_value = data.get("week")
    week = WeekService.resolve_week(week_value) if week_value is not None else None
    actor = resolve_request_context(request)
    created_by = request.user if isinstance(request.user, User) else None

    create_input = TaskCreateInput(
        board=board,
        title=data["title"],
        column=column,
        description=data.get("description", ""),
        week=week,
        priority=data.get("priority", "normal"),
        tag_slugs=data.get("tags"),
        due_at=data.get("due_at"),
        evidence_url=data.get("evidence_url", ""),
        reminder_enabled=data.get("reminder_enabled", True),
        actor=actor,
        created_by=created_by,
    )
    return TaskCreationService.create(create_input)
