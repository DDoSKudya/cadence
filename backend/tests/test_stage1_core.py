import pytest
from django.urls import reverse

from apps.core.models import ApiKey


@pytest.mark.django_db
def test_session_login_me_and_logout(client, django_user_model):
    django_user_model.objects.create_user(
        username="owner",
        email="owner@example.com",
        password="secret-pass",
    )

    login_response = client.post(
        reverse("auth-login"),
        {"username": "owner", "password": "secret-pass"},
        content_type="application/json",
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["username"] == "owner"

    me_response = client.get(reverse("auth-me"))

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "owner@example.com"

    logout_response = client.post(reverse("auth-logout"))

    assert logout_response.status_code == 204


@pytest.mark.django_db
def test_api_key_allows_settings_access(client):
    api_key, raw_key = ApiKey.issue("imports")

    response = client.get(
        reverse("settings"),
        HTTP_AUTHORIZATION=f"Api-Key {raw_key}",
    )

    assert response.status_code == 200
    assert response.json()["timezone"] == "Europe/Moscow"

    api_key.refresh_from_db()
    assert api_key.last_used_at is not None


@pytest.mark.django_db
def test_seed_tags_are_available(client):
    _api_key, raw_key = ApiKey.issue("ui")

    response = client.get(
        reverse("tag-list"),
        HTTP_AUTHORIZATION=f"Api-Key {raw_key}",
    )

    assert response.status_code == 200
    assert {tag["slug"] for tag in response.json()} >= {"backend", "frontend"}
