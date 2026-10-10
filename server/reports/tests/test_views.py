from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from core.models import BankSampah, Nasabah, WasteType
from deposits.models import Deposit


@pytest.fixture
def reports_view_setup(db):
    bank_a = BankSampah.objects.create(name="Bank A", is_demo=False)
    bank_b = BankSampah.objects.create(name="Bank B", is_demo=False)

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

    n_a = Nasabah.objects.create(bank_sampah=bank_a, name="Nasabah A", normalized_name="nasabah a")
    n_b = Nasabah.objects.create(bank_sampah=bank_b, name="Nasabah B", normalized_name="nasabah b")

    wt_kardus = WasteType.objects.create(
        code="kardus",
        name_id="Kardus",
        emission_factor_kgco2e_per_kg=Decimal("0.800"),
        emission_factor_source="KLHK 2024",
    )

    Deposit.objects.create(
        bank_sampah=bank_a,
        nasabah=n_a,
        waste_type=wt_kardus,
        weight_kg=Decimal("100.000"),
        deposit_date=date(2026, 9, 10),
        source="confirmed",
    )
    Deposit.objects.create(
        bank_sampah=bank_b,
        nasabah=n_b,
        waste_type=wt_kardus,
        weight_kg=Decimal("50.000"),
        deposit_date=date(2026, 9, 10),
        source="confirmed",
    )

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)

    client_b = APIClient()
    client_b.force_authenticate(user=user_b)

    unauthed = APIClient()

    return {
        "bank_a": bank_a,
        "bank_b": bank_b,
        "client_a": client_a,
        "client_b": client_b,
        "unauthed": unauthed,
    }


def test_dashboard_summary_success_and_cache_control(reports_view_setup):
    client = reports_view_setup["client_a"]
    resp = client.get("/api/dashboard/summary/?from=2026-09-01&to=2026-09-30")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers.get("Cache-Control") == "no-store"

    data = resp.json()
    assert data["period"]["from"] == "2026-09-01"
    assert data["period"]["to"] == "2026-09-30"
    assert data["totals"]["weight_kg"] == "100.000"
    assert data["totals"]["co2e_kg"] == "80.000"
    assert data["totals"]["deposit_count"] == 1
    assert data["totals"]["active_nasabah"] == 1


def test_dashboard_summary_default_dates(reports_view_setup):
    client = reports_view_setup["client_a"]
    resp = client.get("/api/dashboard/summary/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "from" in data["period"]
    assert "to" in data["period"]


def test_dashboard_summary_validation_errors(reports_view_setup):
    client = reports_view_setup["client_a"]

    resp1 = client.get("/api/dashboard/summary/?from=invalid-date")
    assert resp1.status_code == status.HTTP_400_BAD_REQUEST
    assert resp1.json()["error_code"] == "VALIDATION_ERROR"

    resp2 = client.get("/api/dashboard/summary/?from=2026-09-30&to=2026-09-01")
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    assert resp2.json()["error_code"] == "VALIDATION_ERROR"


def test_dashboard_summary_unauthenticated(reports_view_setup):
    client = reports_view_setup["unauthed"]
    resp = client.get("/api/dashboard/summary/")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_dashboard_summary_cross_bank_isolation(reports_view_setup):
    client_b = reports_view_setup["client_b"]
    resp = client_b.get("/api/dashboard/summary/?from=2026-09-01&to=2026-09-30")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["totals"]["weight_kg"] == "50.000"
    assert data["totals"]["co2e_kg"] == "40.000"


def test_impact_report_success_and_cache_control(reports_view_setup):
    client = reports_view_setup["client_a"]
    resp = client.get("/api/reports/impact/?month=2026-09")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers.get("Cache-Control") == "no-store"

    data = resp.json()
    assert data["period"]["month"] == "2026-09"
    assert data["figures"]["weight_kg"] == "100.000"
    assert data["figures"]["co2e_kg"] == "80.000"
    assert data["figures"]["deposit_count"] == 1
    assert data["narrative"]["source"] == "template"
    assert data["narrative"]["verified"] is True
    assert "100.000 kg" in data["narrative"]["text"]


def test_impact_report_default_month(reports_view_setup):
    client = reports_view_setup["client_a"]
    resp = client.get("/api/reports/impact/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "month" in data["period"]


def test_impact_report_validation_errors(reports_view_setup):
    client = reports_view_setup["client_a"]
    resp = client.get("/api/reports/impact/?month=bad-format")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_impact_report_unauthenticated(reports_view_setup):
    client = reports_view_setup["unauthed"]
    resp = client.get("/api/reports/impact/")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_impact_report_cross_bank_isolation(reports_view_setup):
    client_b = reports_view_setup["client_b"]
    resp = client_b.get("/api/reports/impact/?month=2026-09")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["figures"]["weight_kg"] == "50.000"
    assert data["figures"]["co2e_kg"] == "40.000"
