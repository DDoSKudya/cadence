from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.core.models import ProjectSettings
from apps.core.telegram_check import (
    TelegramBotCheckResult,
    check_telegram_bot,
    run_telegram_bot_check,
)


@pytest.mark.django_db
def test_check_telegram_bot_without_token():
    result = check_telegram_bot("")
    assert result.ok is False
    assert "Токен" in result.message


@pytest.mark.django_db
def test_run_telegram_bot_check_persists_result():
    settings_obj = ProjectSettings.load()
    mock_user = MagicMock(username="my_bot")

    with patch("apps.core.telegram_check.asyncio.run", return_value=mock_user):
        result = run_telegram_bot_check(settings_obj, token="123:abc")

    settings_obj.refresh_from_db()
    assert result.ok is True
    assert settings_obj.telegram_bot_check_ok is True
    assert settings_obj.telegram_bot_checked_at is not None
    assert settings_obj.telegram_bot_username == "@my_bot"


@pytest.mark.django_db
def test_telegram_bot_check_api(client, django_user_model):
    user = django_user_model.objects.create_user(username="admin", password="admin")
    client.force_login(user)
    settings_obj = ProjectSettings.load()
    settings_obj.telegram_bot_token = "123:abc"
    settings_obj.save(update_fields=["telegram_bot_token"])

    with patch(
        "apps.core.views.run_telegram_bot_check",
        return_value=TelegramBotCheckResult(
            ok=True,
            message="@cadence_bot",
            checked_at=timezone.now(),
            bot_username="cadence_bot",
        ),
    ) as mock_run:
        response = client.post(
            "/api/v1/settings/telegram/check/",
            data={},
            content_type="application/json",
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["bot_username"] == "cadence_bot"
    mock_run.assert_called_once()
