from typing import Protocol

from apps.jobs.exceptions import JobError
from apps.jobs.models import BackgroundJob


class JobHandler(Protocol):
    def dispatch(self, job: BackgroundJob) -> None: ...


_handlers: dict[str, JobHandler] = {}


def register_handler(job_type: str, handler: JobHandler) -> None:
    _handlers[job_type] = handler


def get_handler(job_type: str) -> JobHandler:
    handler = _handlers.get(job_type)
    if handler is None:
        raise JobError(f"Unsupported job type: {job_type}")
    return handler
