from apps.imports.models import ImportLog


def list_import_logs() -> list[ImportLog]:
    return list(ImportLog.objects.all()[:200])


def get_import_log(import_id: int) -> ImportLog:
    return ImportLog.objects.get(pk=import_id)
