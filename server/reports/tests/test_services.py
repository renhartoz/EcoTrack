from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from accounts.models import User
from core.models import BankSampah, Nasabah, WasteType
from deposits.models import Deposit
from ingestion.models import ExtractedRow, Extraction, Upload
from reports.services.dashboard import (
    get_current_month_range_jakarta,
    get_dashboard_summary,
)
from reports.services.impact import (
    build_narrative_template,
    get_current_month_jakarta,
    get_impact_report,
)


@pytest.fixture
def service_setup(db):
    bank = BankSampah.objects.create(name="Bank Test", is_demo=False)
    user = User.objects.create_user(
        username="op_test",
        password="Password123",
        bank_sampah=bank,
    )
    nasabah_1 = Nasabah.objects.create(bank_sampah=bank, name="Budi", normalized_name="budi")
    nasabah_2 = Nasabah.objects.create(bank_sampah=bank, name="Siti", normalized_name="siti")

    wt_pet = WasteType.objects.create(
        code="pet",
        name_id="Plastik PET",
        emission_factor_kgco2e_per_kg=Decimal("1.500"),
        emission_factor_source="IPCC 2006",
        emission_factor_note="Avoided virgin PET emissions",
    )
    wt_kardus = WasteType.objects.create(
        code="kardus",
        name_id="Kardus",
        emission_factor_kgco2e_per_kg=Decimal("0.800"),
        emission_factor_source="KLHK 2024",
        emission_factor_note="Avoided landfill methane",
    )
    wt_besi = WasteType.objects.create(
        code="besi",
        name_id="Besi",
        emission_factor_kgco2e_per_kg=None,
    )

    return {
        "bank": bank,
        "user": user,
        "nasabah_1": nasabah_1,
        "nasabah_2": nasabah_2,
        "wt_pet": wt_pet,
        "wt_kardus": wt_kardus,
        "wt_besi": wt_besi,
    }


def test_empty_state_summary(service_setup):
    bank = service_setup["bank"]
    from_date = date(2026, 9, 1)
    to_date = date(2026, 9, 30)

    summary = get_dashboard_summary(bank, from_date, to_date)
    assert summary["totals"]["weight_kg"] == "0.000"
    assert summary["totals"]["co2e_kg"] == "0.000"
    assert summary["totals"]["deposit_count"] == 0
    assert summary["totals"]["active_nasabah"] == 0
    assert summary["by_type"] == []
    assert summary["monthly"] == []
    assert summary["pipeline"]["pending_rows"] == 0
    assert summary["pipeline"]["auto_rate"] == 0.0
    assert summary["pipeline"]["correction_rate"] == 0.0
    assert summary["coverage"]["types_missing_factor"] == []
    assert summary["is_demo"] is False


def test_aggregates_with_and_without_factors(service_setup):
    bank = service_setup["bank"]
    n1 = service_setup["nasabah_1"]
    wt_pet = service_setup["wt_pet"]
    wt_kardus = service_setup["wt_kardus"]
    wt_besi = service_setup["wt_besi"]

    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_pet,
        weight_kg=Decimal("10.000"),
        deposit_date=date(2026, 9, 10),
        source="manual",
    )
    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_kardus,
        weight_kg=Decimal("20.000"),
        deposit_date=date(2026, 9, 15),
        source="confirmed",
    )
    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_besi,
        weight_kg=Decimal("5.000"),
        deposit_date=date(2026, 9, 20),
        source="manual",
    )

    from_date = date(2026, 9, 1)
    to_date = date(2026, 9, 30)
    summary = get_dashboard_summary(bank, from_date, to_date)

    assert summary["totals"]["weight_kg"] == "35.000"
    assert summary["totals"]["co2e_kg"] == "31.000"
    assert summary["totals"]["deposit_count"] == 3
    assert summary["totals"]["active_nasabah"] == 1

    by_type_map = {item["waste_type"]: item for item in summary["by_type"]}
    assert by_type_map["kardus"]["co2e_kg"] == "16.000"
    assert by_type_map["pet"]["co2e_kg"] == "15.000"
    assert by_type_map["besi"]["co2e_kg"] is None

    assert summary["coverage"]["types_missing_factor"] == ["besi"]


def test_date_range_boundaries_and_soft_deleted_excluded(service_setup):
    bank = service_setup["bank"]
    n1 = service_setup["nasabah_1"]
    wt_pet = service_setup["wt_pet"]

    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_pet,
        weight_kg=Decimal("1.000"),
        deposit_date=date(2026, 8, 31),
        source="manual",
    )
    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_pet,
        weight_kg=Decimal("2.000"),
        deposit_date=date(2026, 9, 1),
        source="manual",
    )
    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_pet,
        weight_kg=Decimal("3.000"),
        deposit_date=date(2026, 9, 30),
        source="manual",
    )
    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_pet,
        weight_kg=Decimal("4.000"),
        deposit_date=date(2026, 10, 1),
        source="manual",
    )
    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_pet,
        weight_kg=Decimal("10.000"),
        deposit_date=date(2026, 9, 15),
        source="manual",
        deleted_at=timezone.now(),
    )

    from_date = date(2026, 9, 1)
    to_date = date(2026, 9, 30)
    summary = get_dashboard_summary(bank, from_date, to_date)

    assert summary["totals"]["weight_kg"] == "5.000"
    assert summary["totals"]["deposit_count"] == 2


def test_jakarta_timezone_helpers():
    start_date, end_date = get_current_month_range_jakarta()
    assert start_date.day == 1
    assert end_date.day in (28, 29, 30, 31)
    assert start_date <= end_date

    now_jkt = timezone.now().astimezone(ZoneInfo("Asia/Jakarta"))
    y, m = get_current_month_jakarta()
    assert y == now_jkt.year
    assert m == now_jkt.month


def test_pipeline_rates_calculation(service_setup):
    bank = service_setup["bank"]
    user = service_setup["user"]
    n1 = service_setup["nasabah_1"]
    wt_pet = service_setup["wt_pet"]

    upload = Upload.objects.create(bank_sampah=bank, created_by=user, source_type="text")
    extraction = Extraction.objects.create(
        upload=upload,
        strategy="text",
        provider="groq",
        model="test",
        raw_response={},
    )

    dep_auto = Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_pet,
        weight_kg=Decimal("5.000"),
        deposit_date=date(2026, 9, 10),
        source="auto",
    )
    ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=0,
        tanggal=date(2026, 9, 10),
        status="saved",
        deposit=dep_auto,
        human_edited=False,
    )

    dep_confirmed = Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_pet,
        weight_kg=Decimal("3.000"),
        deposit_date=date(2026, 9, 12),
        source="confirmed",
    )
    ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=1,
        tanggal=date(2026, 9, 12),
        status="saved",
        deposit=dep_confirmed,
        human_edited=True,
    )

    ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=2,
        tanggal=date(2026, 9, 14),
        status="rejected",
        human_edited=False,
    )

    ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=3,
        status="pending",
    )

    summary = get_dashboard_summary(bank, date(2026, 9, 1), date(2026, 9, 30))
    pipeline = summary["pipeline"]

    assert pipeline["pending_rows"] == 1
    assert pipeline["auto_rate"] == 0.33
    assert pipeline["correction_rate"] == 0.33


def test_impact_report_and_deterministic_narrative(service_setup):
    bank = service_setup["bank"]
    n1 = service_setup["nasabah_1"]
    wt_pet = service_setup["wt_pet"]

    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=n1,
        waste_type=wt_pet,
        weight_kg=Decimal("12.500"),
        deposit_date=date(2026, 9, 5),
        source="confirmed",
    )

    report = get_impact_report(bank, 2026, 9)
    assert report["period"]["month"] == "2026-09"
    assert report["figures"]["weight_kg"] == "12.500"
    assert report["figures"]["co2e_kg"] == "18.750"
    assert report["figures"]["deposit_count"] == 1
    assert report["figures"]["active_nasabah"] == 1

    narrative = report["narrative"]
    assert narrative["source"] == "template"
    assert narrative["verified"] is True
    assert "September 2026" in narrative["text"]
    assert "12.500 kg" in narrative["text"]
    assert "18.750 kg CO2e" in narrative["text"]

    factors = report["methodology"]["factors"]
    assert any(f["waste_type"] == "pet" and f["factor"] == "1.500" for f in factors)


def test_empty_narrative_template():
    figures = {
        "weight_kg": "0.000",
        "co2e_kg": "0.000",
        "deposit_count": 0,
        "active_nasabah": 0,
    }
    narrative = build_narrative_template(2026, 9, figures)
    assert narrative["source"] == "template"
    assert narrative["verified"] is True
    assert "belum ada setoran" in narrative["text"]
