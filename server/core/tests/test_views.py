import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from core.models import BankSampah, Nasabah, WasteType


@pytest.fixture
def core_setup(db):
    bank_a = BankSampah.objects.create(name="Bank A")
    bank_b = BankSampah.objects.create(name="Bank B")

    user_a = User.objects.create_user(
        username="user_a",
        password="Password123",
        bank_sampah=bank_a,
    )
    user_b = User.objects.create_user(
        username="user_b",
        password="Password123",
        bank_sampah=bank_b,
    )

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)

    client_b = APIClient()
    client_b.force_authenticate(user=user_b)

    nasabah_a = Nasabah.objects.create(
        bank_sampah=bank_a,
        name="Siti",
        normalized_name="siti",
    )
    nasabah_b = Nasabah.objects.create(
        bank_sampah=bank_b,
        name="Bambang",
        normalized_name="bambang",
    )

    waste_type = WasteType.objects.create(code="pet", name_id="Plastik PET (botol)")

    return {
        "bank_a": bank_a,
        "bank_b": bank_b,
        "user_a": user_a,
        "user_b": user_b,
        "client_a": client_a,
        "client_b": client_b,
        "nasabah_a": nasabah_a,
        "nasabah_b": nasabah_b,
        "waste_type": waste_type,
    }


def test_nasabah_list_and_search(core_setup):
    client = core_setup["client_a"]
    bank_a = core_setup["bank_a"]
    Nasabah.objects.create(bank_sampah=bank_a, name="Budi", normalized_name="budi")

    res = client.get("/api/nasabah/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["count"] == 2

    res_search = client.get("/api/nasabah/?q=sit")
    assert res_search.status_code == status.HTTP_200_OK
    results = res_search.json()["results"]
    assert len(results) == 1
    assert results[0]["name"] == "Siti"


def test_nasabah_create(core_setup):
    client = core_setup["client_a"]

    res = client.post("/api/nasabah/", {"name": "Pak Joko"}, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["name"] == "Pak Joko"
    assert data["normalized_name"] == "pak joko"

    res_dup = client.post("/api/nasabah/", {"name": "Pak Joko"}, format="json")
    assert res_dup.status_code == status.HTTP_400_BAD_REQUEST


def test_nasabah_detail_and_patch(core_setup):
    client = core_setup["client_a"]
    nasabah = core_setup["nasabah_a"]

    res_get = client.get(f"/api/nasabah/{nasabah.id}/")
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.json()["name"] == "Siti"

    res_patch = client.patch(
        f"/api/nasabah/{nasabah.id}/",
        {"name": "Siti Aminah"},
        format="json",
    )
    assert res_patch.status_code == status.HTTP_200_OK
    assert res_patch.json()["name"] == "Siti Aminah"
    assert res_patch.json()["normalized_name"] == "siti aminah"


def test_waste_types_list(core_setup):
    client = core_setup["client_a"]
    res = client.get("/api/waste-types/")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert len(data) >= 1
    assert data[0]["code"] == "pet"


def test_nasabah_cross_bank_404(core_setup):
    client_b = core_setup["client_b"]
    nasabah_a = core_setup["nasabah_a"]

    res_get = client_b.get(f"/api/nasabah/{nasabah_a.id}/")
    assert res_get.status_code == status.HTTP_404_NOT_FOUND

    res_patch = client_b.patch(f"/api/nasabah/{nasabah_a.id}/", {"name": "Hacked"})
    assert res_patch.status_code == status.HTTP_404_NOT_FOUND
