import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from core.models import BankSampah, Nasabah, WasteType
from deposits.models import Deposit


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def active_waste_types(db):
    return [
        WasteType.objects.create(code="pet", name_id="Plastik PET", is_active=True),
        WasteType.objects.create(code="kardus", name_id="Kardus", is_active=True),
    ]


@pytest.mark.django_db
def test_register_demo_auto_generated(client, active_waste_types):
    response = client.post("/api/auth/register-demo/", {}, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert "user" in data
    assert "credentials" in data
    assert data["user"]["bank_sampah"]["is_demo"] is True

    username = data["credentials"]["username"]
    password = data["credentials"]["password"]
    assert username.startswith("juri_")
    assert password == "DemoJudge2026!"

    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies
    assert "csrftoken" in response.cookies

    user = User.objects.get(username=username)
    assert user.bank_sampah.is_demo is True
    assert Nasabah.objects.filter(bank_sampah=user.bank_sampah).count() == 12
    assert Deposit.objects.filter(bank_sampah=user.bank_sampah).count() >= 60


@pytest.mark.django_db
def test_register_demo_custom_credentials(client, active_waste_types):
    payload = {
        "username": "custom_judge",
        "password": "CustomPassword123!",
        "bank_name": "Bank Sampah Khusus Juri",
    }
    response = client.post("/api/auth/register-demo/", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["user"]["username"] == "custom_judge"
    assert data["user"]["bank_sampah"]["name"] == "Bank Sampah Khusus Juri"
    assert data["user"]["bank_sampah"]["is_demo"] is True

    login_res = client.post(
        "/api/auth/login/",
        {"username": "custom_judge", "password": "CustomPassword123!"},
        format="json",
    )
    assert login_res.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_register_demo_duplicate_username(client, active_waste_types):
    bank = BankSampah.objects.create(name="Bank A", is_demo=False)
    User.objects.create_user(username="taken_user", password="Pass12345!", bank_sampah=bank)

    response = client.post("/api/auth/register-demo/", {"username": "taken_user"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
def test_register_demo_isolation(client, active_waste_types):
    res1 = client.post("/api/auth/register-demo/", {}, format="json")
    res2 = client.post("/api/auth/register-demo/", {}, format="json")

    assert res1.status_code == status.HTTP_201_CREATED
    assert res2.status_code == status.HTTP_201_CREATED

    user1 = User.objects.get(id=res1.json()["user"]["id"])
    user2 = User.objects.get(id=res2.json()["user"]["id"])

    assert user1.bank_sampah.id != user2.bank_sampah.id
    deposits_user1 = Deposit.objects.filter(bank_sampah=user1.bank_sampah)
    deposits_user2 = Deposit.objects.filter(bank_sampah=user2.bank_sampah)
    assert deposits_user1.count() > 0
    assert deposits_user2.count() > 0
    assert not deposits_user1.filter(bank_sampah=user2.bank_sampah).exists()
