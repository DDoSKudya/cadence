from django.db import transaction

from apps.boards.models import BoardColumn, SystemType
from apps.boards.services import ColumnSettingsService
from apps.core.models import ProjectSettings
from apps.tasks.events import EventActor
from apps.tasks.models import ActorType, Task, TaskSource
from apps.tasks.services import TaskCloseService
from apps.weeks.models import Week
from apps.weeks.services import WeekService

SYSTEM_ACTOR = EventActor(ActorType.SYSTEM, "", TaskSource.SYSTEM)


class WeekRolloverService:
    @staticmethod
    def process() -> int:
        return WeekRolloverService.process_for_week(
            WeekService.get_or_create_current_week(),
        )

    @staticmethod
    @transaction.atomic
    def process_for_week(current_week: Week) -> int:
        settings = ProjectSettings.load()
        stored_year = settings.week_rollover_iso_year
        stored_week = settings.week_rollover_iso_week

        if (
            stored_year == current_week.iso_year
            and stored_week == current_week.iso_week
        ):
            return 0

        closed_count = 0
        if stored_year is not None and stored_week is not None:
            closed_count = WeekRolloverService._close_ready_tasks()

        settings.week_rollover_iso_year = current_week.iso_year
        settings.week_rollover_iso_week = current_week.iso_week
        settings.save(
            update_fields=[
                "week_rollover_iso_year",
                "week_rollover_iso_week",
                "updated_at",
            ],
        )
        return closed_count

    @staticmethod
    def _close_ready_tasks() -> int:
        board = ColumnSettingsService.get_default_board()
        ready_column = BoardColumn.objects.filter(
            board=board,
            system_type=SystemType.READY,
            is_active=True,
        ).first()
        if ready_column is None:
            return 0

        tasks = list(
            Task.objects.select_for_update()
            .filter(
                board=board,
                column=ready_column,
                archived_at__isnull=True,
            )
            .order_by("id"),
        )
        for task in tasks:
            TaskCloseService.close_with_actor(
                task,
                completion_note="",
                actor=SYSTEM_ACTOR,
            )
        return len(tasks)
