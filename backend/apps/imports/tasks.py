from celery import shared_task
from django.db.utils import DatabaseError, OperationalError

from apps.imports.services import JsonImportService


@shared_task(
    name="apps.imports.tasks.scan_json_inbox",
    queue="imports",
    autoretry_for=(OperationalError, DatabaseError),
    retry_backoff=True,
    max_retries=3,
)
def scan_json_inbox() -> int:
    return JsonImportService.scan_inbox()
