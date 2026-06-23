import pytest
from django.urls import reverse
from rest_framework import serializers

from apps.core.models import ApiKey
from apps.core.serializers import normalize_telegram_recipients


@pytest.mark.django_db
def test_auth_ec_no_auth_returns_unauthorized_or_forbidden(anon_client):
    response = anon_client.get(reverse("settings"))
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_auth_ec_valid_api_key_allows_settings_and_tags(api_client):
    settings_response = api_client.get(reverse("settings"))
    tags_response = api_client.get(reverse("tag-list"))
    assert settings_response.status_code == 200
    assert settings_response.json()["language"] == "en"
    assert tags_response.status_code == 200


@pytest.mark.django_db
def test_auth_ec_invalid_api_key_rejected(client):
    client.defaults["HTTP_AUTHORIZATION"] = "Api-Key invalid"
    response = client.get(reverse("settings"))
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_auth_ec_session_login_logout_me_flow(client, django_user_model):
    django_user_model.objects.create_user(username="alice", password="secret")
    login = client.post(
        reverse("auth-login"),
        {"username": "alice", "password": "secret"},
        content_type="application/json",
    )
    assert login.status_code == 200
    me = client.get(reverse("auth-me"))
    assert me.status_code == 200
    assert me.json()["username"] == "alice"
    logout = client.post(reverse("auth-logout"))
    assert logout.status_code == 204
    me_after_logout = client.get(reverse("auth-me"))
    assert me_after_logout.status_code in {401, 403}


@pytest.mark.django_db
def test_auth_ec_invalid_login_credentials_rejected(client, django_user_model):
    django_user_model.objects.create_user(username="bob", password="secret")
    response = client.post(
        reverse("auth-login"),
        {"username": "bob", "password": "wrong"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "Invalid credentials." in str(response.json())


@pytest.mark.django_db
def test_auth_ec_session_user_accesses_settings_and_tags(session_client):
    settings_response = session_client.get(reverse("settings"))
    tags_response = session_client.get(reverse("tag-list"))
    assert settings_response.status_code == 200
    assert tags_response.status_code == 200


@pytest.mark.django_db
def test_auth_ec_settings_language_can_be_updated(api_client):
    response = api_client.patch(
        reverse("settings"),
        {"language": "ru"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["language"] == "ru"


@pytest.mark.django_db
def test_auth_ec_settings_language_rejects_unknown_locale(api_client):
    response = api_client.patch(
        reverse("settings"),
        {"language": "de"},
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_auth_ec_api_key_verify_empty_returns_none():
    assert ApiKey.verify("") is None


@pytest.mark.django_db
def test_auth_ec_api_key_verify_valid_returns_record():
    issued, raw_key = ApiKey.issue("unit")
    resolved = ApiKey.verify(raw_key)
    assert resolved is not None
    assert resolved.id == issued.id


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(
            [{"chat_id": "100", "kind": "user", "label": "Alice"}],
            [{"chat_id": "100", "kind": "user", "label": "Alice"}],
            id="ec_recipient_valid_user",
        ),
        pytest.param(
            [{"chat_id": "200", "kind": "group", "label": ""}],
            [{"chat_id": "200", "kind": "group", "label": ""}],
            id="ec_recipient_valid_group",
        ),
    ],
)
def test_auth_ec_normalize_telegram_recipients_valid(value, expected):
    assert normalize_telegram_recipients(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param([1], id="ec_recipient_non_object_item"),
        pytest.param([{"kind": "user"}], id="ec_recipient_missing_chat_id"),
        pytest.param(
            [{"chat_id": "1", "kind": "channel"}],
            id="ec_recipient_invalid_kind",
        ),
        pytest.param(
            [
                {"chat_id": "1", "kind": "user"},
                {"chat_id": "1", "kind": "group"},
            ],
            id="ec_recipient_duplicate_chat_id",
        ),
    ],
)
def test_auth_ec_normalize_telegram_recipients_invalid(value):
    with pytest.raises(serializers.ValidationError):
        normalize_telegram_recipients(value)
