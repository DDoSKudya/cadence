from pathlib import Path
from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.imports.job_handlers import JsonInboxScanHandler
from apps.imports.models import ImportLog, ImportStatus
from apps.imports.services import JsonImportService
from apps.imports.validators import ImportValidationError, validate_import_payload
from apps.jobs.models import JobType
from apps.jobs.services import JobService
from conftest import import_payload, upload_import, write_json


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        pytest.param(
            [], "root value must be an object", id="ec_root_non_object_invalid"
        ),
        pytest.param(
            {"schema_version": "2.0", "idempotency_key": "k", "tasks": [{}]},
            "unsupported schema_version",
            id="ec_schema_version_unsupported_invalid",
        ),
        pytest.param(
            {"schema_version": "1.0", "idempotency_key": "", "tasks": [{}]},
            "missing required field: idempotency_key",
            id="ec_idempotency_blank_invalid",
        ),
    ],
)
def test_validate_import_payload_ec_invalid_root_fields_raise_error(
    payload,
    expected_message,
):
    with pytest.raises(ImportValidationError) as exc:
        validate_import_payload(payload)
    assert expected_message in exc.value.message


@pytest.mark.parametrize(
    ("key_size", "is_valid"),
    [
        pytest.param(180, True, id="ec_idempotency_length_180_valid"),
        pytest.param(181, False, id="ec_idempotency_length_181_invalid"),
    ],
)
def test_validate_import_payload_ec_idempotency_key_boundary(key_size, is_valid):
    payload = import_payload(idempotency_key="k" * key_size)
    if is_valid:
        result = validate_import_payload(payload)
        assert result.idempotency_key == "k" * key_size
    else:
        with pytest.raises(ImportValidationError) as exc:
            validate_import_payload(payload)
        assert "idempotency_key is too long" in exc.value.message


@pytest.mark.parametrize(
    ("week_value", "is_valid"),
    [
        pytest.param("2026-W01", True, id="ec_week_iso_format_valid"),
        pytest.param("2026-W53", True, id="ec_week_upper_boundary_valid"),
        pytest.param("2026-W00", False, id="ec_week_below_boundary_invalid"),
        pytest.param("2026-01", False, id="ec_week_wrong_shape_invalid"),
    ],
)
def test_validate_import_payload_ec_week_formats(week_value, is_valid):
    payload = import_payload(week=week_value)
    if is_valid:
        result = validate_import_payload(payload)
        assert result.week == week_value
    else:
        with pytest.raises(ImportValidationError) as exc:
            validate_import_payload(payload)
        assert "invalid week format" in exc.value.message


@pytest.mark.parametrize(
    ("priority", "is_valid"),
    [
        pytest.param("low", True, id="ec_priority_low_valid"),
        pytest.param("normal", True, id="ec_priority_normal_valid"),
        pytest.param("high", True, id="ec_priority_high_valid"),
        pytest.param("urgent", False, id="ec_priority_unknown_invalid"),
        pytest.param(None, True, id="ec_priority_none_defaults_valid"),
    ],
)
def test_validate_import_payload_ec_priority_enum(priority, is_valid):
    payload = import_payload(
        tasks=[{"title": "P", "column": "planned", "priority": priority}]
    )
    if is_valid:
        result = validate_import_payload(payload)
        assert result.tasks[0].priority in {"low", "normal", "high"}
    else:
        with pytest.raises(ImportValidationError) as exc:
            validate_import_payload(payload)
        assert "invalid priority" in exc.value.message


@pytest.mark.parametrize(
    ("due_at", "is_valid"),
    [
        pytest.param("2026-06-22T09:30:00Z", True, id="ec_due_at_rfc3339_z_valid"),
        pytest.param("2026-06-22T09:30:00+03:00", True, id="ec_due_at_offset_valid"),
        pytest.param("", True, id="ec_due_at_empty_treated_as_none_valid"),
        pytest.param("not-a-date", False, id="ec_due_at_malformed_invalid"),
    ],
)
def test_validate_import_payload_ec_due_at(due_at, is_valid):
    payload = import_payload(
        tasks=[{"title": "Due", "column": "planned", "due_at": due_at}]
    )
    if is_valid:
        result = validate_import_payload(payload)
        assert result.tasks[0].title == "Due"
    else:
        with pytest.raises(ImportValidationError) as exc:
            validate_import_payload(payload)
        assert "due_at is invalid" in exc.value.message


@pytest.mark.django_db
def test_json_import_service_ec_valid_payload_creates_tasks(inbox_dirs):
    payload = import_payload()
    pending_file = inbox_dirs["pending"] / "valid.json"
    write_json(pending_file, payload)
    result = JsonImportService.process_file("valid.json")
    assert result.import_log.status == ImportStatus.SUCCEEDED
    assert result.import_log.tasks_created == 1


@pytest.mark.django_db
def test_json_import_service_ec_invalid_payload_marks_failed(inbox_dirs):
    pending_file = inbox_dirs["pending"] / "invalid.json"
    write_json(pending_file, {"schema_version": "1.0", "tasks": []})
    result = JsonImportService.process_file("invalid.json")
    assert result.import_log.status == ImportStatus.FAILED
    assert "idempotency_key" in result.import_log.error_message


@pytest.mark.django_db
def test_json_import_service_ec_duplicate_payload_skips_second_import(inbox_dirs):
    payload = import_payload(idempotency_key="dup-key")
    write_json(inbox_dirs["pending"] / "first.json", payload)
    write_json(inbox_dirs["pending"] / "second.json", payload)
    first = JsonImportService.process_file("first.json")
    second = JsonImportService.process_file("second.json")
    assert first.import_log.status == ImportStatus.SUCCEEDED
    assert second.skipped_duplicate is True
    assert second.import_log.status in {
        ImportStatus.SUCCEEDED,
        ImportStatus.SKIPPED_DUPLICATE,
    }


@pytest.mark.django_db
def test_json_import_service_ec_unknown_column_marks_failed(inbox_dirs):
    payload = import_payload(
        tasks=[{"title": "X", "column": "missing-column", "priority": "normal"}]
    )
    write_json(inbox_dirs["pending"] / "unknown-column.json", payload)
    result = JsonImportService.process_file("unknown-column.json")
    assert result.import_log.status == ImportStatus.FAILED
    assert "unknown column" in result.import_log.error_message


@pytest.mark.django_db
def test_import_api_ec_upload_list_retry_and_scan(api_client, inbox_dirs):
    valid = upload_import(
        api_client, import_payload(idempotency_key="upload-ok"), "upload-ok.json"
    )
    assert valid.status_code == 200
    import_id = valid.json()["id"]
    listed = api_client.get(reverse("import-list"))
    assert listed.status_code == 200
    assert any(item["id"] == import_id for item in listed.json())

    failed = upload_import(
        api_client,
        {"schema_version": "1.0", "idempotency_key": "retry-key", "tasks": []},
        "retry-fail.json",
    )
    assert failed.status_code == 200
    failed_id = failed.json()["id"]
    failed_name = failed.json()["filename"]
    write_json(
        inbox_dirs["failed"] / failed_name,
        import_payload(
            idempotency_key="retry-key",
            tasks=[{"title": "Retried", "column": "planned"}],
        ),
    )
    retried = api_client.post(reverse("import-retry", args=[failed_id]))
    assert retried.status_code == 200
    assert retried.json()["status"] == ImportStatus.SUCCEEDED

    write_json(
        inbox_dirs["pending"] / "scan-me.json",
        import_payload(idempotency_key="scan-key"),
    )
    scanned = api_client.post(reverse("import-scan"))
    assert scanned.status_code == 202
    assert scanned.json()["processed"] >= 1


@pytest.mark.django_db
def test_json_inbox_scan_handler_ec_dispatches_celery_delay():
    job = JobService.create(JobType.JSON_INBOX_SCAN, {})
    with patch("apps.imports.tasks.scan_json_inbox.delay") as mocked_delay:
        JsonInboxScanHandler().dispatch(job)
    mocked_delay.assert_called_once_with(job.id)


@pytest.mark.django_db
def test_import_api_ec_retry_non_failed_rejected(api_client):
    log = ImportLog.objects.create(
        filename="ok.json",
        original_path=str(Path("/tmp/ok.json")),
        checksum="abc",
        idempotency_key="ok-idem",
        schema_version="1.0",
        status=ImportStatus.SUCCEEDED,
    )
    response = api_client.post(reverse("import-retry", args=[log.id]))
    assert response.status_code == 400
