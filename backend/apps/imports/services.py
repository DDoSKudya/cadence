import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.utils import DatabaseError, OperationalError
from django.utils import timezone
from django.utils.text import get_valid_filename, slugify

from apps.boards.models import BoardColumn
from apps.boards.services import ColumnSettingsService
from apps.core.models import ProjectSettings, Tag
from apps.imports.models import ImportLog, ImportStatus
from apps.imports.validators import (
    ImportFilePayload,
    ImportValidationError,
    validate_import_payload,
)
from apps.tasks.events import EventActor, record_task_event
from apps.tasks.models import ActorType, TaskEventType, TaskSource
from apps.tasks.services import TaskCreateInput, TaskCreationService
from apps.weeks.services import WeekService


@dataclass(frozen=True)
class InboxPaths:
    pending: Path
    processing: Path
    processed: Path
    failed: Path

    @classmethod
    def from_settings(cls) -> "InboxPaths":
        return cls(
            pending=Path(settings.TASK_INBOX_PENDING_DIR),
            processing=Path(settings.TASK_INBOX_PROCESSING_DIR),
            processed=Path(settings.TASK_INBOX_PROCESSED_DIR),
            failed=Path(settings.TASK_INBOX_FAILED_DIR),
        )

    def ensure_dirs(self) -> None:
        for path in (self.pending, self.processing, self.processed, self.failed):
            path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ImportProcessResult:
    import_log: ImportLog
    skipped_duplicate: bool = False


class JsonImportService:
    @staticmethod
    def scan_inbox() -> int:
        if not ProjectSettings.load().json_inbox_enabled:
            return 0

        paths = InboxPaths.from_settings()
        paths.ensure_dirs()

        processed = 0
        for file_path in sorted(paths.pending.glob("*.json")):
            JsonImportService.process_file(file_path.name)
            processed += 1
        return processed

    @staticmethod
    def process_file(filename: str) -> ImportProcessResult:
        paths = InboxPaths.from_settings()
        paths.ensure_dirs()

        pending_path = paths.pending / filename
        if not pending_path.exists():
            raise FileNotFoundError(filename)

        processing_path = paths.processing / filename
        shutil.move(pending_path, processing_path)
        return JsonImportService._process_at_path(processing_path, filename)

    @staticmethod
    def upload_and_process(original_name: str, content: bytes) -> ImportProcessResult:
        paths = InboxPaths.from_settings()
        paths.ensure_dirs()

        filename = JsonImportService._upload_filename(original_name)
        pending_path = paths.pending / filename
        pending_path.write_bytes(content)
        return JsonImportService.process_file(filename)

    @staticmethod
    def _upload_filename(original_name: str) -> str:
        filename = get_valid_filename(Path(original_name).name)
        if not filename.lower().endswith(".json"):
            raise ImportValidationError("file must have .json extension")

        paths = InboxPaths.from_settings()
        pending_path = paths.pending / filename
        if pending_path.exists():
            stem = filename[:-5]
            filename = f"{stem}-{uuid.uuid4().hex[:8]}.json"

        return filename

    @staticmethod
    def retry_import(import_log: ImportLog) -> ImportProcessResult:
        if import_log.status != ImportStatus.FAILED:
            raise ImportValidationError("Only failed imports can be retried.")

        paths = InboxPaths.from_settings()
        paths.ensure_dirs()

        failed_path = paths.failed / import_log.filename
        if not failed_path.exists():
            raise FileNotFoundError(import_log.filename)

        processing_path = paths.processing / import_log.filename
        shutil.move(failed_path, processing_path)
        return JsonImportService._process_at_path(
            processing_path,
            import_log.filename,
            existing_log=import_log,
        )

    @staticmethod
    def _process_at_path(
        file_path: Path,
        filename: str,
        *,
        existing_log: ImportLog | None = None,
    ) -> ImportProcessResult:
        paths = InboxPaths.from_settings()
        raw_bytes = file_path.read_bytes()
        checksum = hashlib.sha256(raw_bytes).hexdigest()

        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JsonImportService._fail_file(
                file_path,
                filename,
                checksum,
                "invalid JSON",
                existing_log=existing_log,
            )

        try:
            payload = validate_import_payload(data)
        except ImportValidationError as exc:
            return JsonImportService._fail_file(
                file_path,
                filename,
                checksum,
                exc.message,
                existing_log=existing_log,
                idempotency_key=_read_idempotency_key(data),
            )

        duplicate = JsonImportService._find_duplicate(payload, checksum)
        if duplicate is not None:
            processed_path = paths.processed / filename
            JsonImportService._move_file(file_path, processed_path)
            skip_log = JsonImportService._log_duplicate_skip(
                filename=filename,
                processed_path=processed_path,
                checksum=checksum,
                payload=payload,
                duplicate=duplicate,
            )
            return ImportProcessResult(import_log=skip_log, skipped_duplicate=True)

        try:
            return JsonImportService._import_payload(
                file_path,
                filename,
                checksum,
                payload,
                existing_log=existing_log,
            )
        except (OperationalError, DatabaseError):
            JsonImportService._move_file(file_path, paths.pending / filename)
            raise

    @staticmethod
    def _import_payload(
        file_path: Path,
        filename: str,
        checksum: str,
        payload: ImportFilePayload,
        *,
        existing_log: ImportLog | None = None,
    ) -> ImportProcessResult:
        paths = InboxPaths.from_settings()
        now = timezone.now()
        board = ColumnSettingsService.get_default_board()
        week = WeekService.resolve_week(payload.week)
        actor = EventActor(
            ActorType.IMPORT,
            payload.idempotency_key,
            TaskSource.JSON_IMPORT,
        )

        try:
            prepared = [
                (item, JsonImportService._resolve_column(board.id, item.column))
                for item in payload.tasks
            ]
        except ImportValidationError as exc:
            return JsonImportService._fail_file(
                file_path,
                filename,
                checksum,
                exc.message,
                existing_log=existing_log,
                idempotency_key=payload.idempotency_key,
            )

        import_log = existing_log
        if import_log is None:
            import_log = ImportLog.objects.create(
                filename=filename,
                original_path=str(file_path),
                checksum=checksum,
                idempotency_key=payload.idempotency_key,
                schema_version=payload.schema_version,
                source_label=payload.source_label,
                status=ImportStatus.PROCESSING,
                started_at=now,
            )
        else:
            import_log.filename = filename
            import_log.original_path = str(file_path)
            import_log.checksum = checksum
            import_log.idempotency_key = payload.idempotency_key
            import_log.schema_version = payload.schema_version
            import_log.source_label = payload.source_label
            import_log.status = ImportStatus.PROCESSING
            import_log.tasks_created = 0
            import_log.error_message = ""
            import_log.started_at = now
            import_log.finished_at = None
            import_log.save()

        try:
            with transaction.atomic():
                tasks_created = 0
                for item, column in prepared:
                    tag_slugs = JsonImportService._resolve_tag_slugs(item.tags)
                    task = TaskCreationService.create(
                        TaskCreateInput(
                            board=board,
                            title=item.title,
                            column=column,
                            actor=actor,
                            description=item.description,
                            week=week,
                            priority=item.priority,
                            tag_slugs=tag_slugs,
                            due_at=JsonImportService._aware_due_at(item.due_at),
                            evidence_url=item.evidence_url,
                            reminder_enabled=item.reminder_enabled,
                            external_ref=item.external_ref,
                        ),
                    )
                    record_task_event(
                        task,
                        TaskEventType.IMPORTED,
                        actor=actor,
                        payload={"import_log_id": import_log.id},
                    )
                    tasks_created += 1
        except ImportValidationError as exc:
            return JsonImportService._fail_file(
                file_path,
                filename,
                checksum,
                exc.message,
                existing_log=import_log,
                idempotency_key=payload.idempotency_key,
            )

        import_log.status = ImportStatus.SUCCEEDED
        import_log.tasks_created = tasks_created
        import_log.finished_at = timezone.now()
        import_log.save(
            update_fields=["status", "tasks_created", "finished_at", "checksum"],
        )
        JsonImportService._move_file(file_path, paths.processed / filename)
        return ImportProcessResult(import_log=import_log)

    @staticmethod
    def _fail_file(
        file_path: Path,
        filename: str,
        checksum: str,
        error_message: str,
        *,
        existing_log: ImportLog | None = None,
        idempotency_key: str | None = None,
    ) -> ImportProcessResult:
        paths = InboxPaths.from_settings()
        now = timezone.now()

        if existing_log is None:
            import_log = ImportLog.objects.create(
                filename=filename,
                original_path=str(file_path),
                checksum=checksum,
                idempotency_key=idempotency_key,
                schema_version="",
                status=ImportStatus.FAILED,
                error_message=error_message,
                started_at=now,
                finished_at=now,
            )
        else:
            import_log = existing_log
            import_log.status = ImportStatus.FAILED
            import_log.error_message = error_message
            import_log.tasks_created = 0
            import_log.finished_at = now
            import_log.save(
                update_fields=[
                    "status",
                    "error_message",
                    "tasks_created",
                    "finished_at",
                ],
            )

        JsonImportService._move_file(file_path, paths.failed / filename)
        return ImportProcessResult(import_log=import_log)

    @staticmethod
    def _log_duplicate_skip(
        *,
        filename: str,
        processed_path: Path,
        checksum: str,
        payload: ImportFilePayload,
        duplicate: ImportLog,
    ) -> ImportLog:
        if ImportLog.objects.filter(
            checksum=checksum,
            status__in=[ImportStatus.SUCCEEDED, ImportStatus.SKIPPED_DUPLICATE],
        ).exists():
            return duplicate

        now = timezone.now()
        return ImportLog.objects.create(
            filename=filename,
            original_path=str(processed_path),
            checksum=checksum,
            idempotency_key=None,
            schema_version=payload.schema_version,
            source_label=payload.source_label,
            status=ImportStatus.SKIPPED_DUPLICATE,
            error_message=f"duplicate of import #{duplicate.id}",
            started_at=now,
            finished_at=now,
        )

    @staticmethod
    def _find_duplicate(payload: ImportFilePayload, checksum: str) -> ImportLog | None:
        by_key = ImportLog.objects.filter(
            idempotency_key=payload.idempotency_key,
            status__in=[ImportStatus.SUCCEEDED, ImportStatus.SKIPPED_DUPLICATE],
        ).first()
        if by_key is not None:
            return by_key

        return ImportLog.objects.filter(
            checksum=checksum,
            status__in=[ImportStatus.SUCCEEDED, ImportStatus.SKIPPED_DUPLICATE],
        ).first()

    @staticmethod
    def _resolve_column(board_id: int, column_ref: str) -> BoardColumn:
        normalized = column_ref.strip().lower()
        columns = BoardColumn.objects.filter(board_id=board_id, is_active=True)

        by_system_type = columns.filter(system_type__iexact=normalized).first()
        if by_system_type is not None:
            return by_system_type

        for column in columns:
            if column.name.strip().lower() == normalized:
                return column

        raise ImportValidationError(f"unknown column: {column_ref}")

    @staticmethod
    def _resolve_tag_slugs(tag_names: list[str]) -> list[str]:
        slugs: list[str] = []
        for name in tag_names:
            slug = slugify(name) or name.strip().lower()
            tag, _created = Tag.objects.get_or_create(
                slug=slug,
                defaults={"name": name.strip()},
            )
            if tag.name != name.strip():
                tag.name = name.strip()
                tag.save(update_fields=["name"])
            slugs.append(tag.slug)
        return slugs

    @staticmethod
    def _aware_due_at(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if timezone.is_naive(value):
            return timezone.make_aware(value, UTC)
        return value

    @staticmethod
    def _move_file(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        shutil.move(source, target)


def _read_idempotency_key(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    value = data.get("idempotency_key")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
