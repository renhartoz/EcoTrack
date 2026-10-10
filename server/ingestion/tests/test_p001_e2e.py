import io
from decimal import Decimal

from django.core.management import call_command
import pytest
from PIL import Image

from accounts.models import User
from core.models import BankSampah, Nasabah
from deposits.models import AuditLog, Deposit
from ingestion.models import ExtractedRow, Upload, UploadImage
from ingestion.services.pipeline import process_upload


def create_sample_jpeg():
    buf = io.BytesIO()
    img = Image.new("RGB", (400, 400), (255, 255, 255))
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def p001_setup(db, monkeypatch):
    call_command("loaddata", "core/fixtures/waste_types.json")

    bank = BankSampah.objects.create(name="Bank Sampah P001", is_demo=False)
    user = User.objects.create_user(username="p001_operator", password="Password123", bank_sampah=bank)

    nasabah_names = [
        "Ambar",
        "Bambang",
        "Danu",
        "Siti",
        "RT",
        "Rina",
        "Sum",
        "Joko",
        "Dewi",
        "Anton",
    ]
    for name in nasabah_names:
        Nasabah.objects.create(bank_sampah=bank, name=name, normalized_name=name.lower())

    monkeypatch.setenv("LLM_MODE", "fake")
    monkeypatch.setenv("EXTRACTION_STRATEGY", "ocr_text")
    monkeypatch.setenv("AUTO_SAVE_ENABLED", "true")

    from django.conf import settings
    settings.LLM_MODE = "fake"
    settings.EXTRACTION_STRATEGY = "ocr_text"
    settings.AUTO_SAVE_ENABLED = True

    return {
        "bank": bank,
        "user": user,
    }


def test_p001_e2e_extraction_and_routing(p001_setup):
    bank = p001_setup["bank"]
    user = p001_setup["user"]

    upload = Upload.objects.create(
        bank_sampah=bank,
        created_by=user,
        source_type="image",
        status="processing",
    )
    UploadImage.objects.create(
        upload=upload,
        content_type="image/jpeg",
        data=create_sample_jpeg(),
    )

    processed = process_upload(upload.id)
    assert processed.status == "ready"

    rows = ExtractedRow.objects.filter(upload=processed).order_by("row_index")
    assert rows.count() == 10

    forbidden_auto_names = [
        "siti",
        "mbah sum",
        "mas danu",
        "pak rt",
        "bu rina",
        "joko",
        "pak edi",
    ]

    for row in rows:
        nama = (row.nama_raw or "").lower()
        for forbidden in forbidden_auto_names:
            if forbidden in nama:
                assert row.route != "auto", f"Row with name '{row.nama_raw}' was routed to 'auto'!"

    auto_rows = rows.filter(route="auto")
    for auto_row in auto_rows:
        assert auto_row.status == "saved"
        assert auto_row.deposit is not None
        assert auto_row.deposit.source == "auto"

    auto_deposits = Deposit.objects.filter(upload=processed, source="auto")
    assert auto_deposits.count() == auto_rows.count()

    auto_audits = AuditLog.objects.filter(bank_sampah=bank, action="auto_save")
    assert auto_audits.count() == auto_rows.count()
    for audit in auto_audits:
        assert audit.actor_label == "system:pipeline"
