import io

import pytest
from django.core.management import call_command
from PIL import Image

from accounts.models import User
from core.models import BankSampah
from ingestion.models import Upload, UploadImage
from ingestion.serializers import UploadDetailSerializer
from ingestion.services.ocr_client import OcrApiError, OcrSpaceClient
from ingestion.services.pipeline import process_upload
from ingestion.services.strategies import (
    OcrTextStrategy,
    TextStrategy,
    VisionStrategy,
)


def create_sample_jpeg():
    buf = io.BytesIO()
    img = Image.new("RGB", (400, 400), (255, 255, 255))
    img.save(buf, format="JPEG")
    return buf.getvalue()


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
    call_command("loaddata", "core/fixtures/waste_types.json")
    UploadImage.objects.create(
        upload=upload,
        content_type="image/jpeg",
        data=create_sample_jpeg(),
    )

    result = process_upload(upload.id)
    assert result.status == "ready"
    assert result.error_code is None
    assert result.extractions.count() == 1
    assert result.rows.count() == 10

    row = result.rows.first()
    assert row.status == "pending"
    assert row.tanggal is not None
    assert row.weight_kg is not None
    assert row.score is not None
    assert row.route in ("manual", "confirm", "auto")


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


@pytest.mark.django_db
def test_pipeline_ocr_text_strategy_ignores_failing_vision(bank_and_user, monkeypatch, settings):
    settings.EXTRACTION_STRATEGY = "ocr_text"

    def fake_vision_extract(*args, **kwargs):
        raise RuntimeError("Vision should never be called when strategy is ocr_text")

    monkeypatch.setattr(VisionStrategy, "extract", fake_vision_extract)

    bank, user = bank_and_user
    upload = Upload.objects.create(
        bank_sampah=bank,
        created_by=user,
        source_type="image",
        image_sha256="img-sha-ocr-test",
        status="processing",
    )
    call_command("loaddata", "core/fixtures/waste_types.json")
    UploadImage.objects.create(
        upload=upload,
        content_type="image/jpeg",
        data=create_sample_jpeg(),
    )

    result = process_upload(upload.id)
    assert result.status == "ready"
    assert result.error_code is None

    latest_extraction = result.extractions.order_by("-created_at").first()
    assert latest_extraction is not None
    assert latest_extraction.strategy == "ocr_text"

    serializer = UploadDetailSerializer(result)
    assert serializer.data["strategy"] == "ocr_text"
    assert serializer.data["ocr_engine"] == "3"
    assert serializer.data["input_tokens"] is not None
    assert serializer.data["output_tokens"] is not None


@pytest.mark.django_db
def test_pipeline_ocr_failure_does_not_fallback_to_vision(bank_and_user, monkeypatch, settings):
    settings.EXTRACTION_STRATEGY = "ocr_text"

    def fake_vision_extract(*args, **kwargs):
        raise RuntimeError("Vision should never be called as fallback")

    def fake_ocr_read(*args, **kwargs):
        raise OcrApiError("Simulated OCR failure")

    monkeypatch.setattr(VisionStrategy, "extract", fake_vision_extract)
    monkeypatch.setattr(OcrSpaceClient, "read", fake_ocr_read)

    bank, user = bank_and_user
    upload = Upload.objects.create(
        bank_sampah=bank,
        created_by=user,
        source_type="image",
        image_sha256="img-sha-ocr-fail",
        status="processing",
    )
    UploadImage.objects.create(
        upload=upload,
        content_type="image/jpeg",
        data=create_sample_jpeg(),
    )

    result = process_upload(upload.id)
    assert result.status == "failed"
    assert result.error_code == "OCR_API_ERROR"
    assert "Simulated OCR failure" in (result.error_message or "")

    serializer = UploadDetailSerializer(result)
    assert serializer.data["strategy"] is None
    assert serializer.data["ocr_engine"] is None
    assert serializer.data["input_tokens"] is None
    assert serializer.data["output_tokens"] is None
    assert serializer.data["error_code"] == "OCR_API_ERROR"
