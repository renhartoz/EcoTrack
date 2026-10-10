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
def deposits_setup(db):
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


def test_deposit_manual_create_and_audit(deposits_setup):
    client = deposits_setup["client_a"]
    nasabah = deposits_setup["nasabah_a"]
    wt = deposits_setup["waste_type"]

    res = client.post(
        "/api/deposits/",
        {
            "nasabah_id": nasabah.id,
            "waste_type_id": wt.id,
            "weight_kg": "3.500",
            "deposit_date": "2026-10-01",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["source"] == "manual"
    assert data["weight_kg"] == "3.500"

    audit = AuditLog.objects.filter(entity_type="deposit", entity_id=data["id"]).first()
    assert audit is not None
    assert audit.action == "create"
    assert audit.actor_label == "user_a"


def test_deposit_list_with_filters(deposits_setup):
    client = deposits_setup["client_a"]
    bank = deposits_setup["bank_a"]
    nasabah = deposits_setup["nasabah_a"]
    wt = deposits_setup["waste_type"]

    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=nasabah,
        waste_type=wt,
        weight_kg=Decimal("1.000"),
        deposit_date=date(2026, 9, 15),
        source="manual",
    )
    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=nasabah,
        waste_type=wt,
        weight_kg=Decimal("2.000"),
        deposit_date=date(2026, 10, 5),
        source="confirmed",
    )

    res_all = client.get("/api/deposits/")
    assert res_all.status_code == status.HTTP_200_OK
    assert res_all.json()["count"] == 2

    res_filtered = client.get("/api/deposits/?from=2026-10-01&source=confirmed")
    assert res_filtered.status_code == status.HTTP_200_OK
    assert res_filtered.json()["count"] == 1
    assert res_filtered.json()["results"][0]["weight_kg"] == "2.000"


def test_deposit_patch_and_audit(deposits_setup):
    client = deposits_setup["client_a"]
    bank = deposits_setup["bank_a"]
    nasabah = deposits_setup["nasabah_a"]
    wt = deposits_setup["waste_type"]

    dep = Deposit.objects.create(
        bank_sampah=bank,
        nasabah=nasabah,
        waste_type=wt,
        weight_kg=Decimal("1.000"),
        deposit_date=date(2026, 9, 15),
        source="manual",
    )

    res = client.patch(f"/api/deposits/{dep.id}/", {"weight_kg": "4.000"}, format="json")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["weight_kg"] == "4.000"

    audit = AuditLog.objects.filter(entity_type="deposit", entity_id=dep.id, action="update").first()
    assert audit is not None
    assert audit.after["weight_kg"] == "4.000"


def test_deposit_soft_delete_undo_and_row_revert(deposits_setup):
    client = deposits_setup["client_a"]
    bank = deposits_setup["bank_a"]
    user = deposits_setup["user_a"]
    nasabah = deposits_setup["nasabah_a"]
    wt = deposits_setup["waste_type"]

    upload = Upload.objects.create(bank_sampah=bank, created_by=user, source_type="text", status="ready")
    extraction = Extraction.objects.create(
        upload=upload, strategy="text", provider="groq", model="qwen", prompt_version="v3", schema_version="v3"
    )

    dep = Deposit.objects.create(
        bank_sampah=bank,
        nasabah=nasabah,
        waste_type=wt,
        weight_kg=Decimal("1.000"),
        deposit_date=date(2026, 9, 15),
        source="confirmed",
        upload=upload,
    )

    row = ExtractedRow.objects.create(
        upload=upload,
        extraction=extraction,
        row_index=1,
        status="saved",
        deposit=dep,
    )

    res_delete = client.delete(f"/api/deposits/{dep.id}/")
    assert res_delete.status_code == status.HTTP_200_OK
    assert res_delete.json()["status"] == "ok"

    dep.refresh_from_db()
    assert dep.deleted_at is not None

    row.refresh_from_db()
    assert row.status == "reverted"

    delete_audit = AuditLog.objects.filter(entity_type="deposit", entity_id=dep.id, action="delete").first()
    assert delete_audit is not None

    row_audit = AuditLog.objects.filter(entity_type="extracted_row", entity_id=row.id, action="revert").first()
    assert row_audit is not None

    res_dup = client.delete(f"/api/deposits/{dep.id}/")
    assert res_dup.status_code == status.HTTP_409_CONFLICT


def test_deposit_cross_bank_404(deposits_setup):
    client_b = deposits_setup["client_b"]
    bank_a = deposits_setup["bank_a"]
    nasabah_a = deposits_setup["nasabah_a"]
    wt = deposits_setup["waste_type"]

    dep_a = Deposit.objects.create(
        bank_sampah=bank_a,
        nasabah=nasabah_a,
        waste_type=wt,
        weight_kg=Decimal("1.000"),
        deposit_date=date(2026, 9, 15),
        source="manual",
    )

    assert client_b.patch(f"/api/deposits/{dep_a.id}/", {"weight_kg": "5.000"}).status_code == 404
    assert client_b.delete(f"/api/deposits/{dep_a.id}/").status_code == 404


def test_deposits_csv_export(deposits_setup):
    client = deposits_setup["client_a"]
    bank = deposits_setup["bank_a"]
    nasabah = deposits_setup["nasabah_a"]
    wt = deposits_setup["waste_type"]

    Deposit.objects.create(
        bank_sampah=bank,
        nasabah=nasabah,
        waste_type=wt,
        weight_kg=Decimal("2.500"),
        deposit_date=date(2026, 10, 1),
        source="confirmed",
    )

    res = client.get("/api/deposits/export/")
    assert res.status_code == status.HTTP_200_OK
    assert "text/csv" in res["Content-Type"]
    assert "no-store" in res["Cache-Control"]

    content = res.content.decode("utf-8")
    lines = content.strip().split("\r\n") if "\r\n" in content else content.strip().split("\n")
    assert lines[0] == "id,nasabah,waste_type,weight_kg,deposit_date,source,created_at"
    assert "Siti,Kardus,2.500,2026-10-01,confirmed" in lines[1]
