from apps.imports.models import ImportLog
from apps.imports.services import ImportProcessResult, JsonImportService
from apps.imports.validators import ImportValidationError
from apps.jobs.handlers import register_handler
from apps.jobs.models import JobType
from apps.jobs.services import JobService


class JsonInboxScanHandler:
    def dispatch(self, job) -> None:
        from apps.imports.tasks import scan_json_inbox

        scan_json_inbox.delay(job.id)


class JsonImportFileHandler:
    def dispatch(self, job) -> None:
        self.run(job)

    @staticmethod
    def run(job) -> None:
        JobService.mark_processing(job)
        try:
            result = JsonImportFileHandler._execute(job)
        except Exception as exc:
            JobService.fail(job, str(exc))
            return

        JobService.succeed(job, JsonImportFileHandler._result(result))

    @staticmethod
    def run_upload(job, original_name: str, content: bytes) -> ImportProcessResult:
        JobService.mark_processing(job)
        try:
            result = JsonImportService.upload_and_process(original_name, content)
        except ImportValidationError as exc:
            JobService.fail(job, exc.message)
            raise
        except Exception as exc:
            JobService.fail(job, str(exc))
            raise

        job.payload = {
            "original_name": original_name,
            "filename": result.import_log.filename,
            "import_log_id": result.import_log.id,
        }
        job.save(update_fields=["payload", "updated_at"])
        JobService.succeed(job, JsonImportFileHandler._result(result))
        return result

    @staticmethod
    def _result(result: ImportProcessResult) -> dict:
        import_log = result.import_log
        return {
            "import_log_id": import_log.id,
            "tasks_created": import_log.tasks_created,
            "skipped_duplicate": result.skipped_duplicate,
            "filename": import_log.filename,
        }

    @staticmethod
    def _execute(job):
        payload = job.payload
        import_log_id = payload.get("import_log_id")
        filename = payload.get("filename")

        if import_log_id is not None:
            import_log = ImportLog.objects.get(pk=import_log_id)
            return JsonImportService.retry_import(import_log)

        if filename:
            return JsonImportService.process_file(filename)

        raise ImportValidationError("import job payload is incomplete")


def register() -> None:
    register_handler(JobType.JSON_INBOX_SCAN, JsonInboxScanHandler())
    register_handler(JobType.JSON_IMPORT_FILE, JsonImportFileHandler())
