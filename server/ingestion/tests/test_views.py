import io
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from core.models import BankSampah
from ingestion.models import Upload, UploadImage
from ingestion.throttling import UploadRateThrottle


@pytest.fixture
def test_setup(db):
    bank_a = BankSampah.objects.create(name="Bank A", is_demo=False)
    bank_b = BankSampah.objects.create(name="Bank B", is_demo=False)

    user_a = User.objects.create_user(
        username="op_a",
        password="Password123",
        bank_sampah=bank_a,
    )
    user_b = User.objects.create_user(
        username="op_b",
        password="Password123",
        bank_sampah=bank_b,
    )

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)

    client_b = APIClient()
    client_b.force_authenticate(user=user_b)

    unauthed_client = APIClient()

    return {
        "bank_a": bank_a,
        "bank_b": bank_b,
        "user_a": user_a,
        "user_b": user_b,
        "client_a": client_a,
        "client_b": client_b,
        "unauthed_client": unauthed_client,
    }


def create_image_file(name="test.jpg", size=(200, 200)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, (255, 0, 0))
    img.save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def test_upload_image_success(test_setup):
    client = test_setup["client_a"]
    img_file = create_image_file()
    source_hash = "a" * 64

    resp = client.post(
        "/api/uploads/",
        {"image": img_file, "source_sha256": source_hash},
        format="multipart",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["source_type"] == "image"
    assert data["status"] == "ready"
    assert data["source_sha256"] == source_hash
    assert len(data["rows"]) == 10
    assert data["counts"]["pending"] == 10


def test_upload_image_invalid_hash(test_setup):
    client = test_setup["client_a"]
    img_file = create_image_file()
    resp = client.post(
        "/api/uploads/",
        {"image": img_file, "source_sha256": "not-a-valid-sha"},
        format="multipart",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    data = resp.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_upload_image_invalid_image(test_setup):
    client = test_setup["client_a"]
    corrupted = SimpleUploadedFile("corrupt.jpg", b"bad-bytes", content_type="image/jpeg")
    resp = client.post(
        "/api/uploads/",
        {"image": corrupted},
        format="multipart",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    data = resp.json()
    assert data["error"]["code"] == "INVALID_IMAGE"


def test_upload_text_success(test_setup):
    client = test_setup["client_a"]
    resp = client.post(
        "/api/uploads/text/",
        {"text": "12/9 Bu Siti botol 2,5 kg"},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["source_type"] == "text"
    assert data["status"] == "ready"
    assert len(data["rows"]) == 10


def test_upload_text_validation_error(test_setup):
    client = test_setup["client_a"]
    resp = client.post("/api/uploads/text/", {"text": ""}, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    data = resp.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_upload_unauthenticated(test_setup):
    client = test_setup["unauthed_client"]
    resp = client.post("/api/uploads/text/", {"text": "hello"}, format="json")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_upload_list_scoped(test_setup):
    bank_a = test_setup["bank_a"]
    bank_b = test_setup["bank_b"]
    user_a = test_setup["user_a"]
    user_b = test_setup["user_b"]
    client_a = test_setup["client_a"]

    Upload.objects.create(bank_sampah=bank_a, created_by=user_a, source_type="text")
    Upload.objects.create(bank_sampah=bank_b, created_by=user_b, source_type="text")

    resp = client_a.get("/api/uploads/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["count"] == 1


def test_upload_detail_and_cross_bank_isolation(test_setup):
    bank_a = test_setup["bank_a"]
    user_a = test_setup["user_a"]
    client_a = test_setup["client_a"]
    client_b = test_setup["client_b"]

    upload = Upload.objects.create(
        bank_sampah=bank_a,
        created_by=user_a,
        source_type="text",
        status="ready",
    )

    resp_a = client_a.get(f"/api/uploads/{upload.id}/")
    assert resp_a.status_code == status.HTTP_200_OK

    resp_b = client_b.get(f"/api/uploads/{upload.id}/")
    assert resp_b.status_code == status.HTTP_404_NOT_FOUND


def test_upload_image_view_and_cross_bank(test_setup):
    bank_a = test_setup["bank_a"]
    user_a = test_setup["user_a"]
    client_a = test_setup["client_a"]
    client_b = test_setup["client_b"]
    unauthed = test_setup["unauthed_client"]

    upload = Upload.objects.create(
        bank_sampah=bank_a,
        created_by=user_a,
        source_type="image",
        status="ready",
    )
    UploadImage.objects.create(
        upload=upload,
        content_type="image/jpeg",
        data=b"image-stream-bytes",
    )

    resp_a = client_a.get(f"/api/uploads/{upload.id}/image/")
    assert resp_a.status_code == status.HTTP_200_OK
    assert resp_a.content == b"image-stream-bytes"
    assert resp_a["Content-Type"] == "image/jpeg"
    assert resp_a["Cache-Control"] == "no-store"

    resp_b = client_b.get(f"/api/uploads/{upload.id}/image/")
    assert resp_b.status_code == status.HTTP_404_NOT_FOUND

    resp_unauthed = unauthed.get(f"/api/uploads/{upload.id}/image/")
    assert resp_unauthed.status_code == status.HTTP_401_UNAUTHORIZED


def test_upload_retry_success(test_setup):
    bank_a = test_setup["bank_a"]
    user_a = test_setup["user_a"]
    client_a = test_setup["client_a"]

    upload = Upload.objects.create(
        bank_sampah=bank_a,
        created_by=user_a,
        source_type="text",
        raw_text="sample text",
        status="failed",
    )

    resp = client_a.post(f"/api/uploads/{upload.id}/retry/", {}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "ready"


def test_upload_retry_fresh_processing_conflict(test_setup):
    bank_a = test_setup["bank_a"]
    user_a = test_setup["user_a"]
    client_a = test_setup["client_a"]

    upload = Upload.objects.create(
        bank_sampah=bank_a,
        created_by=user_a,
        source_type="text",
        raw_text="sample text",
        status="processing",
        processing_started_at=timezone.now() - timedelta(seconds=30),
    )

    resp = client_a.post(f"/api/uploads/{upload.id}/retry/", {}, format="json")
    assert resp.status_code == status.HTTP_409_CONFLICT
    data = resp.json()
    assert data["error"]["code"] == "UPLOAD_PROCESSING"


def test_upload_retry_stale_processing_allowed(test_setup):
    bank_a = test_setup["bank_a"]
    user_a = test_setup["user_a"]
    client_a = test_setup["client_a"]

    upload = Upload.objects.create(
        bank_sampah=bank_a,
        created_by=user_a,
        source_type="text",
        raw_text="sample text",
        status="processing",
        processing_started_at=timezone.now() - timedelta(seconds=150),
    )

    resp = client_a.post(f"/api/uploads/{upload.id}/retry/", {}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "ready"


def test_upload_retry_cross_bank_404(test_setup):
    bank_a = test_setup["bank_a"]
    user_a = test_setup["user_a"]
    client_b = test_setup["client_b"]

    upload = Upload.objects.create(
        bank_sampah=bank_a,
        created_by=user_a,
        source_type="text",
        status="failed",
    )

    resp = client_b.post(f"/api/uploads/{upload.id}/retry/", {}, format="json")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_upload_throttle_exceeded(test_setup, monkeypatch):
    from django.core.cache import cache

    cache.clear()

    client = test_setup["client_a"]
    monkeypatch.setitem(
        UploadRateThrottle.THROTTLE_RATES,
        "upload",
        "1/hour",
    )

    resp1 = client.post("/api/uploads/text/", {"text": "Deposit 1"}, format="json")
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = client.post("/api/uploads/text/", {"text": "Deposit 2"}, format="json")
    assert resp2.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    data = resp2.json()
    assert data["error"]["code"] == "THROTTLED"
