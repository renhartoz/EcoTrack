from datetime import timedelta
import pytest
from django.core.cache import cache
from django.middleware.csrf import _get_new_csrf_string, _mask_cipher_secret
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from accounts.models import User
from core.models import BankSampah

@pytest.fixture(autouse=True)
def clear_db_cache():
    cache.clear()
    yield
    cache.clear()

@pytest.fixture
def bank():
    return BankSampah.objects.create(
        name="Bank Sampah Uji",
        city="Yogyakarta",
        is_demo=False,
    )

@pytest.fixture
def operator_user(bank):
    user = User.objects.create_user(
        username="operator_test",
        password="ValidPassword123",
        bank_sampah=bank,
    )
    return user

@pytest.fixture
def api_client():
    return APIClient()

def setup_csrf(client):
    secret = _get_new_csrf_string()
    masked_cookie = _mask_cipher_secret(secret)
    masked_header = _mask_cipher_secret(secret)
    client.cookies["csrftoken"] = masked_cookie
    return masked_header

@pytest.mark.django_db
def test_login_success_sets_httponly_and_csrf_cookies(api_client, operator_user):
    payload = {"username": "operator_test", "password": "ValidPassword123"}
    response = api_client.post("/api/auth/login/", payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert "user" in response.data
    assert response.data["user"]["username"] == "operator_test"
    assert response.data["user"]["bank_sampah"]["name"] == "Bank Sampah Uji"

    assert "access_token" in response.cookies
    assert response.cookies["access_token"]["httponly"] is True
    assert response.cookies["access_token"]["samesite"] == "Lax"
    assert response.cookies["access_token"]["path"] == "/api/"

    assert "refresh_token" in response.cookies
    assert response.cookies["refresh_token"]["httponly"] is True
    assert response.cookies["refresh_token"]["samesite"] == "Lax"
    assert response.cookies["refresh_token"]["path"] == "/api/auth/"

    assert "csrftoken" in response.cookies
    assert response.cookies["csrftoken"]["httponly"] is False

@pytest.mark.django_db
def test_login_invalid_credentials_returns_401_unauthenticated(api_client, operator_user):
    payload = {"username": "operator_test", "password": "WrongPassword"}
    response = api_client.post("/api/auth/login/", payload, format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["error"]["code"] == "UNAUTHENTICATED"

@pytest.mark.django_db
def test_login_with_stale_access_cookie_succeeds(api_client, operator_user):
    stale_token = AccessToken.for_user(operator_user)
    stale_token.set_exp(lifetime=-timedelta(minutes=10))
    api_client.cookies["access_token"] = str(stale_token)

    payload = {"username": "operator_test", "password": "ValidPassword123"}
    response = api_client.post("/api/auth/login/", payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["user"]["username"] == "operator_test"

@pytest.mark.django_db
def test_refresh_success_rotates_and_blacklists_old(api_client, operator_user):
    old_refresh = RefreshToken.for_user(operator_user)
    api_client.cookies["refresh_token"] = str(old_refresh)
    csrf_header = setup_csrf(api_client)

    response = api_client.post(
        "/api/auth/refresh/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_header,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"status": "ok"}
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies
    assert response.cookies["refresh_token"].value != str(old_refresh)

    second_response = api_client.post(
        "/api/auth/refresh/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_header,
    )
    assert second_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert second_response.data["error"]["code"] == "UNAUTHENTICATED"

@pytest.mark.django_db
def test_refresh_succeeds_with_expired_access_cookie(api_client, operator_user):
    expired_access = AccessToken.for_user(operator_user)
    expired_access.set_exp(lifetime=-timedelta(minutes=10))
    api_client.cookies["access_token"] = str(expired_access)

    valid_refresh = RefreshToken.for_user(operator_user)
    api_client.cookies["refresh_token"] = str(valid_refresh)
    csrf_header = setup_csrf(api_client)

    response = api_client.post(
        "/api/auth/refresh/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_header,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"status": "ok"}

@pytest.mark.django_db
def test_refresh_without_csrf_returns_403_csrf_failed(api_client, operator_user):
    valid_refresh = RefreshToken.for_user(operator_user)
    api_client.cookies["refresh_token"] = str(valid_refresh)
    api_client.cookies["csrftoken"] = _mask_cipher_secret(_get_new_csrf_string())

    response = api_client.post("/api/auth/refresh/", {}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["error"]["code"] == "CSRF_FAILED"

@pytest.mark.django_db
def test_logout_blacklists_refresh_token_and_clears_cookies(api_client, operator_user):
    refresh = RefreshToken.for_user(operator_user)
    access = AccessToken.for_user(operator_user)

    api_client.cookies["refresh_token"] = str(refresh)
    api_client.cookies["access_token"] = str(access)
    csrf_header = setup_csrf(api_client)

    response = api_client.post(
        "/api/auth/logout/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_header,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"status": "ok"}
    assert response.cookies["access_token"].value == ""
    assert response.cookies["refresh_token"].value == ""

    api_client.cookies["refresh_token"] = str(refresh)
    refresh_attempt = api_client.post(
        "/api/auth/refresh/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_header,
    )
    assert refresh_attempt.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_logout_with_expired_access_cookie_succeeds(api_client, operator_user):
    expired_access = AccessToken.for_user(operator_user)
    expired_access.set_exp(lifetime=-timedelta(minutes=10))
    api_client.cookies["access_token"] = str(expired_access)

    refresh = RefreshToken.for_user(operator_user)
    api_client.cookies["refresh_token"] = str(refresh)
    csrf_header = setup_csrf(api_client)

    response = api_client.post(
        "/api/auth/logout/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_header,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.cookies["access_token"].value == ""
    assert response.cookies["refresh_token"].value == ""

@pytest.mark.django_db
def test_logout_without_csrf_returns_403_csrf_failed(api_client, operator_user):
    refresh = RefreshToken.for_user(operator_user)
    api_client.cookies["refresh_token"] = str(refresh)
    api_client.cookies["csrftoken"] = _mask_cipher_secret(_get_new_csrf_string())

    response = api_client.post("/api/auth/logout/", {}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["error"]["code"] == "CSRF_FAILED"

@pytest.mark.django_db
def test_me_authenticated_returns_user_and_sets_csrf_cookie(api_client, operator_user):
    access = AccessToken.for_user(operator_user)
    api_client.cookies["access_token"] = str(access)

    response = api_client.get("/api/auth/me/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["username"] == "operator_test"
    assert response.data["bank_sampah"]["name"] == "Bank Sampah Uji"
    assert "csrftoken" in response.cookies

@pytest.mark.django_db
def test_me_unauthenticated_returns_401_unauthenticated_not_403(api_client):
    response = api_client.get("/api/auth/me/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["error"]["code"] == "UNAUTHENTICATED"

@pytest.mark.django_db
def test_unsafe_method_with_access_cookie_without_csrf_returns_403_csrf_failed(api_client, operator_user):
    access = AccessToken.for_user(operator_user)
    api_client.cookies["access_token"] = str(access)
    api_client.cookies["csrftoken"] = _mask_cipher_secret(_get_new_csrf_string())

    response = api_client.post("/api/auth/me/", {}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["error"]["code"] == "CSRF_FAILED"
