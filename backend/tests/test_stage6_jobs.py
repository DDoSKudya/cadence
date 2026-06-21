import json

import pytest
from django.urls import reverse

from apps.core.models import ApiKey
from apps.imports.models import ImportStatus
from apps.imports.services import JsonImportService
from apps.jobs.models import BackgroundJob, JobStatus, JobType
from apps.jobs.services import JobService


@pytest.fixture
def api_client_auth(client):
    api_key, raw_key = ApiKey.issue("jobs-tests")
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
    return {"pending": pending}


def sample_payload(**overrides):
    payload = {
        "schema_version": "1.0",
        "idempotency_key": "jobs-import",
        "tasks": [{"title": "Job import task", "column": "planned"}],
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_job_service_lifecycle():
    job = JobService.create(JobType.JSON_INBOX_SCAN, {"source": "test"})
    JobService.mark_processing(job, celery_task_id="celery-1")
    JobService.succeed(job, {"processed": 2})

    job.refresh_from_db()
    assert job.status == JobStatus.SUCCEEDED
    assert job.result == {"processed": 2}
    assert job.celery_task_id == "celery-1"
    assert job.attempts == 1


@pytest.mark.django_db
def test_upload_creates_background_job(api_client_auth, inbox_dirs):
    from django.core.files.uploadedfile import SimpleUploadedFile

    client, _api_key = api_client_auth
    payload = sample_payload(idempotency_key="job-upload")
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
    job = BackgroundJob.objects.get(job_type=JobType.JSON_IMPORT_FILE)
    assert job.status == JobStatus.SUCCEEDED
    assert job.result["tasks_created"] == 1


@pytest.mark.django_db
def test_jobs_list_and_detail_api(api_client_auth):
    client, _api_key = api_client_auth
    job = JobService.create(JobType.JSON_INBOX_SCAN, {})
    JobService.mark_processing(job)
    JobService.fail(job, "scan failed")

    list_response = client.get(reverse("job-list"))
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["count"] == 1
    assert len(payload["results"]) == 1

    detail_response = client.get(reverse("job-detail", args=[job.id]))
    assert detail_response.status_code == 200
    assert detail_response.json()["last_error"] == "scan failed"


@pytest.mark.django_db
def test_jobs_list_pagination(api_client_auth):
    client, _api_key = api_client_auth
    for index in range(25):
        JobService.create(JobType.JSON_INBOX_SCAN, {"batch": index})

    first_page = client.get(reverse("job-list"), {"page": 1, "page_size": 10})
    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert first_payload["count"] == 25
    assert first_payload["page"] == 1
    assert first_payload["page_size"] == 10
    assert len(first_payload["results"]) == 10

    second_page = client.get(reverse("job-list"), {"page": 3, "page_size": 10})
    second_payload = second_page.json()
    assert len(second_payload["results"]) == 5


@pytest.mark.django_db
def test_retry_failed_import_job(api_client_auth, inbox_dirs):
    client, _api_key = api_client_auth
    base = inbox_dirs["pending"].parent
    pending = inbox_dirs["pending"]
    failed_dir = base / "failed"

    pending_path = pending / "retry-job.json"
    pending_path.write_text(
        json.dumps(
            {"schema_version": "1.0", "idempotency_key": "retry-job", "tasks": []},
        ),
        encoding="utf-8",
    )

    failed = JsonImportService.process_file("retry-job.json")
    assert failed.import_log.status == ImportStatus.FAILED

    job = JobService.create(
        JobType.JSON_IMPORT_FILE,
        {
            "filename": "retry-job.json",
            "import_log_id": failed.import_log.id,
        },
    )
    JobService.mark_processing(job)
    JobService.fail(job, "previous failure")

    (failed_dir / "retry-job.json").write_text(
        json.dumps(sample_payload(idempotency_key="retry-job-fixed")),
        encoding="utf-8",
    )

    response = client.post(reverse("job-retry", args=[job.id]))
    assert response.status_code == 200
    assert response.json()["status"] == JobStatus.SUCCEEDED


@pytest.mark.django_db
def test_cancel_pending_job(api_client_auth):
    client, _api_key = api_client_auth
    job = JobService.create(JobType.JSON_INBOX_SCAN, {})

    response = client.post(reverse("job-cancel", args=[job.id]))
    assert response.status_code == 200
    assert response.json()["status"] == JobStatus.CANCELLED


@pytest.mark.django_db
def test_retry_failed_job_stays_failed_when_payload_incomplete(api_client_auth):
    client, _api_key = api_client_auth
    job = JobService.create(JobType.JSON_IMPORT_FILE, {"original_name": "broken.json"})
    JobService.mark_processing(job)
    JobService.fail(job, "upload failed before filename was saved")

    response = client.post(reverse("job-retry", args=[job.id]))
    assert response.status_code == 200
    assert response.json()["status"] == JobStatus.FAILED
    assert "incomplete" in response.json()["last_error"]


@pytest.mark.django_db
def test_scan_task_records_background_job(inbox_dirs):
    from apps.imports.tasks import scan_json_inbox

    path = inbox_dirs["pending"] / "beat.json"
    path.write_text(
        json.dumps(sample_payload(idempotency_key="beat-job")),
        encoding="utf-8",
    )

    processed = scan_json_inbox.run()
    assert processed == 1

    job = BackgroundJob.objects.get(job_type=JobType.JSON_INBOX_SCAN)
    assert job.status == JobStatus.SUCCEEDED
    assert job.result["processed"] == 1
