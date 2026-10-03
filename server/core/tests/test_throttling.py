import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from core.models import BankSampah

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()

@pytest.fixture
def operator(db):
    bank = BankSampah.objects.create(name="Bank Throttle")
    return User.objects.create_user(
        username="throttle_user",
        password="ValidPassword123",
        bank_sampah=bank,
    )

@pytest.mark.django_db
def test_login_throttling_keyed_by_username(operator):
    client = APIClient()
    payload = {"username": "throttle_user", "password": "WrongPassword"}

    for _ in range(5):
        res = client.post("/api/auth/login/", payload, format="json")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    throttled_res = client.post("/api/auth/login/", payload, format="json")
    assert throttled_res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert throttled_res.data["error"]["code"] == "THROTTLED"

    other_payload = {"username": "other_user", "password": "WrongPassword"}
    other_res = client.post("/api/auth/login/", other_payload, format="json")
    assert other_res.status_code == status.HTTP_401_UNAUTHORIZED
