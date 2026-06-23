from apps.analytics.tasks import run_analytics_export
from apps.jobs.handlers import register_handler
from apps.jobs.models import JobType


class AnalyticsExportHandler:
    def dispatch(self, job) -> None:
        run_analytics_export.delay(job.id)


def register() -> None:
    register_handler(JobType.ANALYTICS_EXPORT, AnalyticsExportHandler())
