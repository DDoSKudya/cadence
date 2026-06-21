import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.core.models import ApiKey
from apps.imports.models import ImportLog, ImportStatus
from apps.imports.services import JsonImportService
from apps.tasks.models import Task


@pytest.fixture
def api_client_auth(client):
    api_key, raw_key = ApiKey.issue("imports-tests")
    client.defaults["HTTP_AUTHORIZATION"] = f"Api-Key {raw_key}"
    return client, api_key


@pytest.fixture
def inbox_dirs(tmp_path, settings):
    pending = tmp_path / "pending"
    processing = tmp_path / "processing"
    processed = tmp_path / "processed"
    failed = tmp_path / "failed"
    for path in (pending, processing, processed, failed):
        path.mkdir()

    settings.TASK_INBOX_PENDING_DIR = str(pending)
    settings.TASK_INBOX_PROCESSING_DIR = str(processing)
    settings.TASK_INBOX_PROCESSED_DIR = str(processed)
    settings.TASK_INBOX_FAILED_DIR = str(failed)
    return {
        "pending": pending,
        "processing": processing,
        "processed": processed,
        "failed": failed,
    }


def write_import_file(folder, name: str, payload: dict) -> None:
    path = folder / name
    path.write_text(json.dumps(payload), encoding="utf-8")


def sample_payload(**overrides):
    payload = {
        "schema_version": "1.0",
        "idempotency_key": "test-import-1",
        "source": "mentor-notes",
        "tasks": [
            {
                "title": "Разобрать Celery Beat",
                "column": "planned",
                "priority": "high",
                "tags": ["backend", "course"],
            }
        ],
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_valid_import_creates_tasks(inbox_dirs):
    write_import_file(inbox_dirs["pending"], "batch.json", sample_payload())

    result = JsonImportService.process_file("batch.json")

    assert result.import_log.status == ImportStatus.SUCCEEDED
    assert result.import_log.tasks_created == 1
    assert Task.objects.filter(
        title="Разобрать Celery Beat",
        source="json_import",
    ).exists()
    assert (inbox_dirs["processed"] / "batch.json").exists()


@pytest.mark.django_db
def test_invalid_schema_fails_import(inbox_dirs):
    write_import_file(
        inbox_dirs["pending"],
        "bad.json",
        {"schema_version": "1.0", "idempotency_key": "bad-empty", "tasks": []},
    )

    result = JsonImportService.process_file("bad.json")

    assert result.import_log.status == ImportStatus.FAILED
    assert "tasks must contain at least one item" in result.import_log.error_message
    assert (inbox_dirs["failed"] / "bad.json").exists()
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_unknown_column_fails_import(inbox_dirs):
    payload = sample_payload(
        idempotency_key="unknown-column",
        tasks=[{"title": "Broken", "column": "review"}],
    )
    write_import_file(inbox_dirs["pending"], "column.json", payload)

    result = JsonImportService.process_file("column.json")

    assert result.import_log.status == ImportStatus.FAILED
    assert "unknown column: review" in result.import_log.error_message


@pytest.mark.django_db
def test_duplicate_idempotency_key_is_skipped(inbox_dirs):
    payload = sample_payload(idempotency_key="dup-key")
    write_import_file(inbox_dirs["pending"], "first.json", payload)
    JsonImportService.process_file("first.json")

    write_import_file(inbox_dirs["pending"], "second.json", payload)
    result = JsonImportService.process_file("second.json")

    assert result.skipped_duplicate is True
    assert result.import_log.status == ImportStatus.SUCCEEDED
    assert Task.objects.filter(source="json_import").count() == 1
    assert (inbox_dirs["processed"] / "second.json").exists()


@pytest.mark.django_db
def test_duplicate_key_different_content_creates_skip_log(inbox_dirs):
    write_import_file(
        inbox_dirs["pending"],
        "first.json",
        sample_payload(idempotency_key="dup-key", tasks=[{"title": "First task"}]),
    )
    JsonImportService.process_file("first.json")

    write_import_file(
        inbox_dirs["pending"],
        "second.json",
        sample_payload(idempotency_key="dup-key", tasks=[{"title": "Second task"}]),
    )
    result = JsonImportService.process_file("second.json")

    assert result.skipped_duplicate is True
    assert result.import_log.status == ImportStatus.SKIPPED_DUPLICATE
    assert Task.objects.filter(source="json_import").count() == 1
    assert ImportLog.objects.filter(status=ImportStatus.SKIPPED_DUPLICATE).count() == 1


@pytest.mark.django_db
def test_invalid_week_fails_import(inbox_dirs):
    write_import_file(
        inbox_dirs["pending"],
        "week.json",
        sample_payload(idempotency_key="bad-week", week="2026-W99"),
    )

    result = JsonImportService.process_file("week.json")

    assert result.import_log.status == ImportStatus.FAILED
    assert "invalid week format" in result.import_log.error_message


@pytest.mark.django_db
def test_partial_batch_failure_creates_no_tasks(inbox_dirs):
    payload = sample_payload(
        idempotency_key="partial-batch",
        tasks=[
            {"title": "Valid task", "column": "planned"},
            {"title": "Broken task", "column": "review"},
        ],
    )
    write_import_file(inbox_dirs["pending"], "partial.json", payload)

    result = JsonImportService.process_file("partial.json")

    assert result.import_log.status == ImportStatus.FAILED
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_import_list_and_scan_api(api_client_auth, inbox_dirs):
    client, _api_key = api_client_auth
    write_import_file(
        inbox_dirs["pending"],
        "api.json",
        sample_payload(idempotency_key="api-import"),
    )

    scan_response = client.post(reverse("import-scan"))
    assert scan_response.status_code == 202
    assert scan_response.json()["processed"] == 1

    list_response = client.get(reverse("import-list"))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["status"] == ImportStatus.SUCCEEDED


@pytest.mark.django_db
def test_upload_import_api(api_client_auth, inbox_dirs):
    client, _api_key = api_client_auth
    payload = sample_payload(idempotency_key="upload-api")
    response = client.post(
        reverse("import-upload"),
        {
            "file": SimpleUploadedFile(
                "upload.json",
                json.dumps(payload).encode(),
                content_type="application/json",
            ),
        },
        format="multipart",
    )

    assert response.status_code == 200
    assert response.json()["status"] == ImportStatus.SUCCEEDED
    assert Task.objects.filter(source="json_import").count() == 1


@pytest.mark.django_db
def test_retry_failed_import(api_client_auth, inbox_dirs):
    write_import_file(
        inbox_dirs["pending"],
        "retry.json",
        {"schema_version": "1.0", "tasks": []},
    )
    failed = JsonImportService.process_file("retry.json")
    assert failed.import_log.status == ImportStatus.FAILED

    write_import_file(
        inbox_dirs["failed"],
        "retry.json",
        sample_payload(idempotency_key="retry-key"),
    )

    client, _api_key = api_client_auth
    response = client.post(reverse("import-retry", args=[failed.import_log.id]))
    assert response.status_code == 200
    assert response.json()["status"] == ImportStatus.SUCCEEDED
