from apps.imports.models import ImportLog


def list_import_logs() -> list[ImportLog]:
    return list(ImportLog.objects.all()[:200])
