from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from core.models import BankSampah, Nasabah, WasteType
from deposits.models import AuditLog, Deposit
from ingestion.models import ExtractedRow, Extraction, Upload


@pytest.fixture
def review_setup(db):
    bank_a = BankSampah.objects.create(name="Bank A")
    bank_b = BankSampah.objects.create(name="Bank B")

    user_a = User.objects.create_user(username="user_a", password="Password123", bank_sampah=bank_a)
    user_b = User.objects.create_user(username="user_b", password="Password123", bank_sampah=bank_b)

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)

    client_b = APIClient()
    client_b.force_authenticate(user=user_b)

    nasabah_a = Nasabah.objects.create(bank_sampah=bank_a, name="Siti", normalized_name="siti")
    nasabah_b = Nasabah.objects.create(bank_sampah=bank_b, name="Bambang", normalized_name="bambang")

    waste_type = WasteType.objects.create(code="kardus", name_id="Kardus")

    upload_a = Upload.objects.create(
        bank_sampah=bank_a,
        created_by=user_a,
        source_type="text",
        status="ready",
    )
    extraction_a = Extraction.objects.create(
        upload=upload_a,
        strategy="text",
        provider="groq",
        model="qwen",
        prompt_version="v3",
        schema_version="v3",
    )

    upload_b = Upload.objects.create(
        bank_sampah=bank_b,
        created_by=user_b,
        source_type="text",
        status="ready",
    )
    extraction_b = Extraction.objects.create(
        upload=upload_b,
        strategy="text",
        provider="groq",
        model="qwen",
        prompt_version="v3",
        schema_version="v3",
    )

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
        "upload_a": upload_a,
        "extraction_a": extraction_a,
        "upload_b": upload_b,
        "extraction_b": extraction_b,
    }


def test_row_patch_success(review_setup):
    client = review_setup["client_a"]
    upload = review_setup["upload_a"]
    extraction = review_setup["extraction_a"]
    nasabah = review_setup["nasabah_a"]
    wt = review_setup["waste_type"]

    row = ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=1,
        status="pending",
        route="manual",
        flags=[{"code": "NASABAH_UNKNOWN", "severity": "hard"}],
        tanggal_raw="01/10",
        nama_raw="Siti",
        jenis_raw="Kardus",
        berat_raw="5",
        satuan_raw="kg",
        tanggal=date(2026, 10, 1),
        nasabah=None,
        waste_type=wt,
        weight_kg=Decimal("5.000"),
    )

    res = client.patch(f"/api/rows/{row.id}/", {"nasabah_id": nasabah.id}, format="json")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["human_edited"] is True
    assert data["route"] == "confirm"
    assert data["normalized"]["nasabah_id"] == nasabah.id
    assert not any(f["code"] == "NASABAH_UNKNOWN" for f in data["flags"])


def test_row_patch_non_pending_returns_409(review_setup):
    client = review_setup["client_a"]
    upload = review_setup["upload_a"]
    extraction = review_setup["extraction_a"]

    row = ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=1,
        status="saved",
    )

    res = client.patch(f"/api/rows/{row.id}/", {"weight_kg": "10.000"}, format="json")
    assert res.status_code == status.HTTP_409_CONFLICT
    assert res.json()["error"]["code"] == "ROW_NOT_PENDING"


def test_row_confirm_success(review_setup):
    client = review_setup["client_a"]
    upload = review_setup["upload_a"]
    extraction = review_setup["extraction_a"]
    nasabah = review_setup["nasabah_a"]
    wt = review_setup["waste_type"]

    row = ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=1,
        status="pending",
        route="confirm",
        flags=[],
        tanggal=date(2026, 10, 1),
        nasabah=nasabah,
        waste_type=wt,
        weight_kg=Decimal("5.000"),
    )

    res = client.post(f"/api/rows/{row.id}/confirm/")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "saved"
    assert data["deposit_id"] is not None

    deposit = Deposit.objects.get(id=data["deposit_id"])
    assert deposit.source == "confirmed"
    assert deposit.weight_kg == Decimal("5.000")

    audit = AuditLog.objects.filter(entity_type="deposit", entity_id=deposit.id).first()
    assert audit is not None
    assert audit.action == "create"


def test_row_double_confirm_returns_409(review_setup):
    client = review_setup["client_a"]
    upload = review_setup["upload_a"]
    extraction = review_setup["extraction_a"]
    nasabah = review_setup["nasabah_a"]
    wt = review_setup["waste_type"]

    row = ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=1,
        status="pending",
        route="confirm",
        flags=[],
        tanggal=date(2026, 10, 1),
        nasabah=nasabah,
        waste_type=wt,
        weight_kg=Decimal("5.000"),
    )

    res1 = client.post(f"/api/rows/{row.id}/confirm/")
    assert res1.status_code == status.HTTP_200_OK

    res2 = client.post(f"/api/rows/{row.id}/confirm/")
    assert res2.status_code == status.HTTP_409_CONFLICT
    assert res2.json()["error"]["code"] == "ROW_NOT_PENDING"
    assert Deposit.objects.filter(upload=upload).count() == 1


def test_row_confirm_with_hard_flags_returns_422(review_setup):
    client = review_setup["client_a"]
    upload = review_setup["upload_a"]
    extraction = review_setup["extraction_a"]
    nasabah = review_setup["nasabah_a"]
    wt = review_setup["waste_type"]

    row = ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=1,
        status="pending",
        flags=[{"code": "ILLEGIBLE_FIELD", "severity": "hard"}],
        tanggal=date(2026, 10, 1),
        nasabah=nasabah,
        waste_type=wt,
        weight_kg=Decimal("5.000"),
    )

    res = client.post(f"/api/rows/{row.id}/confirm/")
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert res.json()["error"]["code"] == "ROW_HAS_HARD_FLAGS"


def test_row_reject_success(review_setup):
    client = review_setup["client_a"]
    upload = review_setup["upload_a"]
    extraction = review_setup["extraction_a"]

    row = ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=1,
        status="pending",
    )

    res = client.post(f"/api/rows/{row.id}/reject/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "rejected"

    res_again = client.post(f"/api/rows/{row.id}/reject/")
    assert res_again.status_code == status.HTTP_409_CONFLICT


def test_upload_confirm_all(review_setup):
    client = review_setup["client_a"]
    upload = review_setup["upload_a"]
    extraction = review_setup["extraction_a"]
    nasabah = review_setup["nasabah_a"]
    wt = review_setup["waste_type"]

    r1 = ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=1,
        status="pending",
        route="confirm",
        flags=[],
        tanggal=date(2026, 10, 1),
        nasabah=nasabah,
        waste_type=wt,
        weight_kg=Decimal("2.000"),
    )
    r2 = ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=2,
        status="pending",
        route="confirm",
        flags=[{"code": "DUPLICATE_IN_PAGE", "severity": "soft"}],
        tanggal=date(2026, 10, 1),
        nasabah=nasabah,
        waste_type=wt,
        weight_kg=Decimal("3.000"),
    )
    r3 = ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=3,
        status="pending",
        route="manual",
        flags=[{"code": "TYPE_UNKNOWN", "severity": "hard"}],
    )

    res = client.post(f"/api/uploads/{upload.id}/confirm-all/")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["confirmed"] == 1
    assert data["skipped"] == 2

    r1.refresh_from_db()
    r2.refresh_from_db()
    assert r1.status == "saved"
    assert r2.status == "pending"


def test_cross_bank_404_on_review_endpoints(review_setup):
    client_b = review_setup["client_b"]
    upload_a = review_setup["upload_a"]
    extraction_a = review_setup["extraction_a"]

    row_a = ExtractedRow.objects.create(
        upload=upload_a,
        extraction=extraction_a,
        row_index=1,
        status="pending",
    )

    res_patch = client_b.patch(f"/api/rows/{row_a.id}/", {"weight_kg": "5.000"})
    assert res_patch.status_code == status.HTTP_404_NOT_FOUND

    res_confirm = client_b.post(f"/api/rows/{row_a.id}/confirm/")
    assert res_confirm.status_code == status.HTTP_404_NOT_FOUND

    res_reject = client_b.post(f"/api/rows/{row_a.id}/reject/")
    assert res_reject.status_code == status.HTTP_404_NOT_FOUND

    res_confirm_all = client_b.post(f"/api/uploads/{upload_a.id}/confirm-all/")
    assert res_confirm_all.status_code == status.HTTP_404_NOT_FOUND
