import pytest

from accounts.models import User
from core.models import BankSampah
from ingestion.models import Upload, UploadImage
from ingestion.services.pipeline import process_upload
from ingestion.services.strategies import (
    OcrTextStrategy,
    TextStrategy,
    VisionStrategy,
)


@pytest.fixture
def bank_and_user(db):
    bank = BankSampah.objects.create(name="Bank Test", is_demo=False)
    user = User.objects.create_user(
        username="op_pipeline",
        password="Password123",
        bank_sampah=bank,
    )
    return bank, user


def test_vision_strategy_execution():
    strategy = VisionStrategy()
    output = strategy.extract(llm_jpeg=b"fake-jpeg-bytes", cache_image_id="test-cache")
    assert len(output.raw_extraction.rows) == 10
    assert output.ocr_lines is None
    assert output.raw_extraction.rows[0].nama_raw == "Bu Ambar"
    assert output.raw_extraction.rows[0].y_min is None
    assert output.raw_extraction.rows[0].y_max is None


def test_ocr_text_strategy_execution():
    strategy = OcrTextStrategy()
    output = strategy.extract(
        ocr_jpeg=b"fake-ocr-jpeg",
        ocr_width=1000,
        ocr_height=1000,
        cache_image_id="test-ocr-cache",
    )
    assert len(output.raw_extraction.rows) == 10
    assert output.ocr_lines is not None
    assert len(output.ocr_lines) == 59


def test_text_strategy_execution():
    strategy = TextStrategy()
    output = strategy.extract(text="12/9 Bu Siti botol 2,5 kg", cache_image_id="text-sha")
    assert len(output.raw_extraction.rows) == 10
    assert output.raw_extraction.rows[0].y_min is None
    assert output.raw_extraction.rows[0].y_max is None


@pytest.mark.django_db
def test_pipeline_process_upload_image_success(bank_and_user):
    bank, user = bank_and_user
    upload = Upload.objects.create(
        bank_sampah=bank,
        created_by=user,
        source_type="image",
        image_sha256="img-sha-123",
        status="processing",
    )
    UploadImage.objects.create(
        upload=upload,
        content_type="image/jpeg",
        data=b"fake-image-bytes",
    )

    result = process_upload(upload.id)
    assert result.status == "ready"
    assert result.error_code is None
    assert result.extractions.count() == 1
    assert result.rows.count() == 10

    row = result.rows.first()
    assert row.status == "pending"
    assert row.tanggal is None
    assert row.nasabah is None
    assert row.waste_type is None
    assert row.weight_kg is None
    assert row.flags == []
    assert row.score is None
    assert row.route is None


@pytest.mark.django_db
def test_pipeline_process_upload_text_success(bank_and_user):
    bank, user = bank_and_user
    upload = Upload.objects.create(
        bank_sampah=bank,
        created_by=user,
        source_type="text",
        raw_text="Sample text",
        status="processing",
    )

    result = process_upload(upload.id)
    assert result.status == "ready"
    assert result.rows.count() == 10


@pytest.mark.django_db
def test_pipeline_reprocess_replaces_pending_rows_only(bank_and_user):
    bank, user = bank_and_user
    upload = Upload.objects.create(
        bank_sampah=bank,
        created_by=user,
        source_type="text",
        raw_text="Sample text",
        status="processing",
    )
    process_upload(upload.id)
    assert upload.rows.count() == 10

    first_row = upload.rows.first()
    first_row.status = "saved"
    first_row.save()

    process_upload(upload.id)
    assert upload.rows.filter(status="saved").count() == 1
    assert upload.rows.filter(status="pending").count() == 10
    assert upload.rows.count() == 11
