from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.models import BankSampah, Nasabah, WasteType
from deposits.models import Deposit
from ingestion.services.validate import validate_page_rows, validate_row_single


def test_date_out_of_range():
    today = date(2026, 10, 10)
    old_date = today - timedelta(days=730)
    flags = validate_row_single(
        nama_raw="Bambang",
        jenis_raw="Kardus",
        berat_raw="5",
        has_correction=False,
        llm_confidence=0.9,
        tanggal=old_date,
        nasabah_id=1,
        waste_type_id=1,
        weight_kg=Decimal("5.000"),
        initial_flags=[],
        today=today,
    )
    assert any(f["code"] == "DATE_OUT_OF_RANGE" for f in flags)


def test_weight_out_of_range():
    today = date(2026, 10, 10)
    flags = validate_row_single(
        nama_raw="Bambang",
        jenis_raw="Kardus",
        berat_raw="250",
        has_correction=False,
        llm_confidence=0.9,
        tanggal=today,
        nasabah_id=1,
        waste_type_id=1,
        weight_kg=Decimal("250.000"),
        initial_flags=[],
        today=today,
        max_weight=200.0,
    )
    assert any(f["code"] == "WEIGHT_OUT_OF_RANGE" for f in flags)


def test_illegible_field():
    today = date(2026, 10, 10)
    flags = validate_row_single(
        nama_raw=None,
        jenis_raw="Kardus",
        berat_raw="5",
        has_correction=False,
        llm_confidence=0.9,
        tanggal=today,
        nasabah_id=1,
        waste_type_id=1,
        weight_kg=Decimal("5.000"),
        initial_flags=[],
        today=today,
    )
    assert any(f["code"] == "ILLEGIBLE_FIELD" for f in flags)


def test_low_llm_confidence():
    today = date(2026, 10, 10)
    flags = validate_row_single(
        nama_raw="Bambang",
        jenis_raw="Kardus",
        berat_raw="5",
        has_correction=False,
        llm_confidence=0.4,
        tanggal=today,
        nasabah_id=1,
        waste_type_id=1,
        weight_kg=Decimal("5.000"),
        initial_flags=[],
        today=today,
    )
    assert any(f["code"] == "LOW_LLM_CONFIDENCE" for f in flags)


def test_duplicate_in_page(db):
    bank = BankSampah.objects.create(name="Bank Test")
    today = date(2026, 10, 10)
    rows = [
        {
            "nama_raw": "Bambang",
            "jenis_raw": "Kardus",
            "berat_raw": "5",
            "tanggal": today,
            "nasabah_id": 1,
            "waste_type_id": 2,
            "weight_kg": Decimal("5.000"),
        },
        {
            "nama_raw": "Bambang",
            "jenis_raw": "Kardus",
            "berat_raw": "5",
            "tanggal": today,
            "nasabah_id": 1,
            "waste_type_id": 2,
            "weight_kg": Decimal("5.000"),
        },
    ]

    results = validate_page_rows(rows, bank_id=bank.id, today=today)
    assert any(f["code"] == "DUPLICATE_IN_PAGE" for f in results[0])
    assert any(f["code"] == "DUPLICATE_IN_PAGE" for f in results[1])


def test_duplicate_in_db(db):
    bank = BankSampah.objects.create(name="Bank Test")
    nasabah = Nasabah.objects.create(bank_sampah=bank, name="Bambang", normalized_name="bambang")
    waste_type = WasteType.objects.create(code="kardus", name_id="Kardus")
    today = date(2026, 10, 10)

    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=nasabah,
        waste_type=waste_type,
        weight_kg=Decimal("5.000"),
        deposit_date=today,
        source="confirmed",
    )

    rows = [
        {
            "nama_raw": "Bambang",
            "jenis_raw": "Kardus",
            "berat_raw": "5",
            "tanggal": today,
            "nasabah_id": nasabah.id,
            "waste_type_id": waste_type.id,
            "weight_kg": Decimal("5.000"),
        }
    ]

    results = validate_page_rows(rows, bank_id=bank.id, today=today)
    assert any(f["code"] == "DUPLICATE_IN_DB" for f in results[0])
