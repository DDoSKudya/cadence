from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.common import celery_logging
from apps.core.models import ProjectSettings
from apps.core.telegram_check import check_telegram_bot
from apps.telegram_bot.bot import build_start_reply, get_bot, parse_callback_data


@pytest.mark.django_db
def test_platform_ec_health_endpoint_ok(api_client):
    response = api_client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db
def test_platform_ec_status_endpoint_returns_services(session_client):
    response = session_client.get(reverse("platform-status"))
    assert response.status_code == 200
    payload = response.json()
    assert "services" in payload
    assert "server_time" in payload
    assert "timezone" in payload
    service_ids = {service["id"] for service in payload["services"]}
    assert service_ids == {"api", "database", "broker", "worker"}
    database = next(
        service for service in payload["services"] if service["id"] == "database"
    )
    assert database["status"] == "ok"


@pytest.mark.django_db
def test_platform_ec_service_logs_endpoint_returns_entries(session_client):
    from apps.common.service_logs import record_service_log

    record_service_log("api", "INFO", "test log line", source="process")
    response = session_client.get(
        reverse("platform-service-logs", kwargs={"service_id": "api"}),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["service_id"] == "api"
    assert "entries" in payload
    assert any(entry["message"] == "test log line" for entry in payload["entries"])


@pytest.mark.django_db
def test_platform_ec_service_logs_newest_first():
    from datetime import timedelta
    from uuid import uuid4

    from django.utils import timezone as dj_timezone

    from apps.common.service_logs import get_service_logs, record_service_log

    token = uuid4().hex[:8]
    older_message = f"older log {token}"
    newer_message = f"newer log {token}"
    now = dj_timezone.now()
    record_service_log(
        "api",
        "INFO",
        older_message,
        source="process",
        logged_at=(now - timedelta(seconds=1)).isoformat(),
    )
    record_service_log(
        "api",
        "INFO",
        newer_message,
        source="process",
        logged_at=now.isoformat(),
    )
    entries = get_service_logs("api", limit=500)
    ours = [entry for entry in entries if token in entry["message"]]
    assert [entry["message"] for entry in ours] == [newer_message, older_message]


@pytest.mark.django_db
def test_platform_ec_service_logs_endpoint_unknown_service(session_client):
    response = session_client.get(
        reverse("platform-service-logs", kwargs={"service_id": "unknown"}),
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_platform_ec_worker_service_logs_include_job_id(session_client):
    from apps.jobs.models import BackgroundJob, JobStatus, JobType

    BackgroundJob.objects.create(
        job_type=JobType.JSON_INBOX_SCAN,
        status=JobStatus.SUCCEEDED,
        result={"processed": 1},
    )
    response = session_client.get(
        reverse("platform-service-logs", kwargs={"service_id": "worker"}),
    )
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert any(entry.get("job_id") for entry in entries)


@pytest.mark.django_db
def test_platform_ec_telegram_check_post_success(session_client):
    with patch("apps.core.telegram_check.asyncio.run") as run_mock:
        run_mock.return_value = SimpleNamespace(username="cadence_bot")
        response = session_client.post(
            reverse("settings-telegram-check"),
            {"telegram_bot_token": "123:ABC"},
            content_type="application/json",
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["bot_username"] == "cadence_bot"


@pytest.mark.django_db
def test_platform_ec_request_id_echoes_header(api_client):
    response = api_client.get(reverse("health"), HTTP_X_REQUEST_ID="ec-request-id")
    assert response.status_code == 200
    assert response["X-Request-ID"] == "ec-request-id"


@pytest.mark.django_db
def test_platform_ec_request_id_generates_when_missing(api_client):
    response = api_client.get(reverse("health"))
    assert response.status_code == 200
    assert response["X-Request-ID"]


@pytest.mark.django_db
def test_platform_ec_openapi_schema_contains_core_paths(api_client):
    response = api_client.get(reverse("schema"), HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})
    assert "/api/v1/tasks/" in paths
    assert "/api/v1/analytics/summary/" in paths
    assert "/api/v1/analytics/exports/preview/" in paths
    assert "/api/v1/jobs/" in paths


@pytest.mark.django_db
def test_platform_ec_nginx_health_path_404(api_client):
    response = api_client.get("/health")
    assert response.status_code == 404


def test_platform_ec_celery_logging_signal_handlers_call_logger():
    sender = SimpleNamespace(name="demo.task")
    with (
        patch.object(celery_logging.logger, "info") as info_mock,
        patch.object(celery_logging.logger, "error") as error_mock,
    ):
        celery_logging.log_task_prerun(
            sender=sender, task_id="t1", args=(1,), kwargs={}
        )
        celery_logging.log_task_postrun(sender=sender, task_id="t1", state="SUCCESS")
        celery_logging.log_task_failure(
            sender=sender, task_id="t1", exception=RuntimeError("x")
        )
    assert info_mock.call_count == 2
    assert error_mock.call_count == 1


@pytest.mark.parametrize(
    ("value", "is_valid"),
    [
        pytest.param(
            "task_done:1:10", True, id="ec_callback_data_valid_with_notification_id"
        ),
        pytest.param(
            "task_snooze:1", True, id="ec_callback_data_valid_without_notification_id"
        ),
        pytest.param("invalid", False, id="ec_callback_data_invalid_shape"),
    ],
)
def test_platform_ec_parse_callback_data_classes(value, is_valid):
    if is_valid:
        action, task_id, notification_id, status_id = parse_callback_data(value)
        assert isinstance(action, str)
        assert task_id > 0
        assert notification_id is None or notification_id > 0
        assert status_id is None or status_id > 0
    else:
        with pytest.raises(ValueError):
            parse_callback_data(value)


@pytest.mark.django_db
def test_platform_ec_build_start_reply_group_and_private():
    settings = ProjectSettings.load()
    settings.language = ProjectSettings.Language.EN
    settings.save(update_fields=["language", "updated_at"])

    group = build_start_reply(chat_id=100, chat_type="group")
    private = build_start_reply(chat_id=200, chat_type="private")
    assert "Group" in group
    assert "Private chat" in private
    assert "<code>100</code>" in group


@pytest.mark.django_db
def test_platform_ec_build_start_reply_russian_locale():
    settings = ProjectSettings.load()
    settings.language = ProjectSettings.Language.RU
    settings.save(update_fields=["language", "updated_at"])

    group = build_start_reply(chat_id=100, chat_type="group")
    private = build_start_reply(chat_id=200, chat_type="private")
    assert "Группа" in group
    assert "Личный чат" in private


@pytest.mark.django_db
def test_platform_ec_get_bot_without_token_raises():
    settings_obj = ProjectSettings.load()
    settings_obj.telegram_bot_token = ""
    settings_obj.save(update_fields=["telegram_bot_token", "updated_at"])
    with pytest.raises(RuntimeError):
        get_bot()


@pytest.mark.django_db
def test_platform_ec_check_telegram_bot_empty_token_returns_error_result():
    settings = ProjectSettings.load()
    settings.language = ProjectSettings.Language.EN
    settings.save(update_fields=["language", "updated_at"])

    result = check_telegram_bot("")
    assert result.ok is False
    assert "not set" in result.message.lower()
