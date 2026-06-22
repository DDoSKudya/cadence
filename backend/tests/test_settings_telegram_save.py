import json
from unittest.mock import patch

import pytest

from apps.core.models import ProjectSettings


@pytest.mark.django_db
def test_patch_telegram_settings_persists(client, django_user_model):
    user = django_user_model.objects.create_user(username="admin", password="admin")
    client.force_login(user)

    payload = {
        "telegram_enabled": True,
        "telegram_bot_token": "123456:ABC-DEF",
        "telegram_bot_username": "@mybot",
        "telegram_recipients": [{"chat_id": "999", "label": "Me", "kind": "user"}],
        "default_reminder_interval_minutes": 1440,
        "stale_in_progress_minutes": 4320,
        "stale_planned_minutes": 10080,
        "quiet_hours_start": None,
        "quiet_hours_end": None,
    }

    with patch("apps.core.serializers.run_telegram_bot_check"):
        response = client.patch(
            "/api/v1/settings/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    assert response.status_code == 200, response.content

    settings_obj = ProjectSettings.load()
    assert settings_obj.telegram_enabled is True
    assert settings_obj.telegram_bot_token == "123456:ABC-DEF"
    assert settings_obj.telegram_bot_username == "@mybot"
    assert settings_obj.telegram_recipients == [
        {"chat_id": "999", "label": "Me", "kind": "user"},
    ]

    body = response.json()
    assert body["telegram_bot_token_set"] is True
    assert body["telegram_recipients"] == payload["telegram_recipients"]


@pytest.mark.django_db
def test_patch_telegram_settings_persists_even_when_bot_check_fails(
    client,
    django_user_model,
):
    user = django_user_model.objects.create_user(username="admin", password="admin")
    client.force_login(user)

    payload = {
        "telegram_enabled": True,
        "telegram_bot_token": "invalid-token",
        "telegram_bot_username": "@mybot",
        "telegram_recipients": [{"chat_id": "999", "label": "Me", "kind": "user"}],
    }

    with patch(
        "apps.core.telegram_check.asyncio.run",
        side_effect=Exception("network error"),
    ):
        response = client.patch(
            "/api/v1/settings/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    assert response.status_code == 200, response.content

    settings_obj = ProjectSettings.load()
    assert settings_obj.telegram_bot_token == "invalid-token"
    assert settings_obj.telegram_recipients[0]["chat_id"] == "999"
