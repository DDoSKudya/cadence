import pytest
from django.urls import reverse
from django.utils import timezone

from apps.jobs.exceptions import JobCancelError, JobRetryError
from apps.jobs.models import BackgroundJob, JobStatus, JobType
from apps.jobs.selectors import parse_datetime_param, parse_int_param
from apps.jobs.services import JobRetryService, JobService


@pytest.mark.django_db
def test_jobs_ec_lifecycle_pending_processing_succeeded():
    job = JobService.create(JobType.JSON_INBOX_SCAN, {"x": 1})
    assert job.status == JobStatus.PENDING
    JobService.mark_processing(job)
    job.refresh_from_db()
    assert job.status == JobStatus.PROCESSING
    assert job.attempts == 1
    JobService.succeed(job, {"processed": 1})
    job.refresh_from_db()
    assert job.status == JobStatus.SUCCEEDED
    assert job.result["processed"] == 1


@pytest.mark.django_db
def test_jobs_ec_lifecycle_processing_failed():
    job = JobService.create(JobType.JSON_IMPORT_FILE, {})
    JobService.mark_processing(job)
    JobService.fail(job, "boom")
    job.refresh_from_db()
    assert job.status == JobStatus.FAILED
    assert job.last_error == "boom"


@pytest.mark.django_db
def test_jobs_ec_cancel_non_pending_fails():
    job = JobService.create(JobType.NOTIFICATION_SCAN, {})
    JobService.mark_processing(job)
    with pytest.raises(JobCancelError):
        JobService.cancel(job)


@pytest.mark.django_db
def test_jobs_ec_retry_failed_only_and_enforces_max_attempts():
    job = BackgroundJob.objects.create(
        job_type=JobType.JSON_IMPORT_FILE,
        status=JobStatus.FAILED,
        attempts=3,
        max_attempts=3,
    )
    with pytest.raises(JobRetryError):
        JobRetryService.retry(job)


@pytest.mark.django_db
def test_jobs_ec_retry_failed_job_resets_and_dispatches():
    job = BackgroundJob.objects.create(
        job_type=JobType.ANALYTICS_EXPORT,
        status=JobStatus.FAILED,
        attempts=1,
        max_attempts=3,
    )

    class DummyHandler:
        def dispatch(self, _job):
            return None

    from apps.jobs import handlers

    handlers.register_handler(JobType.ANALYTICS_EXPORT, DummyHandler())
    retried = JobRetryService.retry(job)
    assert retried.status in {
        JobStatus.PENDING,
        JobStatus.SUCCEEDED,
        JobStatus.PROCESSING,
    }


@pytest.mark.django_db
def test_jobs_ec_list_filters_by_status_and_job_type(api_client):
    old = timezone.now() - timezone.timedelta(days=1)
    BackgroundJob.objects.create(
        job_type=JobType.JSON_INBOX_SCAN, status=JobStatus.PENDING, created_at=old
    )
    target = BackgroundJob.objects.create(
        job_type=JobType.NOTIFICATION_SCAN, status=JobStatus.FAILED
    )
    response = api_client.get(
        reverse("job-list"),
        {"status": JobStatus.FAILED, "job_type": JobType.NOTIFICATION_SCAN},
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["results"]}
    assert target.id in ids


@pytest.mark.parametrize(
    ("value", "default", "minimum", "maximum", "expected"),
    [
        pytest.param(None, 20, 1, 100, 20, id="ec_int_none_uses_default"),
        pytest.param("abc", 20, 1, 100, 20, id="ec_int_invalid_uses_default"),
        pytest.param("0", 20, 1, 100, 1, id="ec_int_below_min_clamped"),
        pytest.param("999", 20, 1, 100, 100, id="ec_int_above_max_clamped"),
        pytest.param("5", 20, 1, 100, 5, id="ec_int_in_range_valid"),
    ],
)
def test_jobs_ec_parse_int_param_classes(value, default, minimum, maximum, expected):
    assert parse_int_param(value, default, minimum=minimum, maximum=maximum) == expected


@pytest.mark.parametrize(
    ("value", "expect_none"),
    [
        pytest.param(None, True, id="ec_datetime_none_returns_none"),
        pytest.param("bad-date", True, id="ec_datetime_invalid_returns_none"),
        pytest.param(
            "2026-06-22T10:00:00Z", False, id="ec_datetime_valid_returns_aware"
        ),
    ],
)
def test_jobs_ec_parse_datetime_param_classes(value, expect_none):
    parsed = parse_datetime_param(value)
    if expect_none:
        assert parsed is None
    else:
        assert parsed is not None
        assert timezone.is_aware(parsed)
