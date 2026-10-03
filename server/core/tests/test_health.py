from datetime import timedelta
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from core.models import BankSampah

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def operator_user(db):
    bank = BankSampah.objects.create(name="Bank Sehat", is_demo=False)
    return User.objects.create_user(
        username="user_sehat",
        password="Password123",
        bank_sampah=bank,
    )

def test_health_check_returns_200_ok(api_client):
    response = api_client.get("/api/health/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"status": "ok"}

@pytest.mark.django_db
def test_health_check_with_stale_access_cookie_succeeds(api_client, operator_user):
    stale_token = AccessToken.for_user(operator_user)
    stale_token.set_exp(lifetime=-timedelta(minutes=10))
    api_client.cookies["access_token"] = str(stale_token)

    response = api_client.get("/api/health/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"status": "ok"}
