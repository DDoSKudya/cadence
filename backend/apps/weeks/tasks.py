from celery import shared_task

from apps.weeks.rollover import WeekRolloverService


@shared_task(name="apps.weeks.tasks.process_week_rollover")
def process_week_rollover() -> int:
    return WeekRolloverService.process()
