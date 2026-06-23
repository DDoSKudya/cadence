import logging

from celery.signals import task_failure, task_postrun, task_prerun

logger = logging.getLogger("cadence.celery")


def _job_ref(args: tuple[object, ...], kwargs: dict[str, object]) -> str:
    if args:
        return str(args[0])
    job_id = kwargs.get("job_id")
    return str(job_id) if job_id is not None else "-"


@task_prerun.connect
def log_task_prerun(
    sender=None,
    task_id=None,
    args=None,
    kwargs=None,
    **extra: object,
) -> None:
    name = sender.name if sender else "unknown"
    logger.info(
        "celery task start name=%s celery_id=%s job_id=%s",
        name,
        task_id,
        _job_ref(args or (), kwargs or {}),
    )


@task_postrun.connect
def log_task_postrun(
    sender=None,
    task_id=None,
    state=None,
    retval=None,
    **extra: object,
) -> None:
    name = sender.name if sender else "unknown"
    logger.info(
        "celery task end name=%s celery_id=%s state=%s",
        name,
        task_id,
        state,
    )


@task_failure.connect
def log_task_failure(
    sender=None,
    task_id=None,
    exception=None,
    **extra: object,
) -> None:
    name = sender.name if sender else "unknown"
    logger.error(
        "celery task failed name=%s celery_id=%s error=%s",
        name,
        task_id,
        exception,
    )
