import io

import pytest
from PIL import Image

from ingestion.services.preprocess import (
    FileTooLargeError,
    InvalidImageError,
    prepare_image,
)


def create_test_image(format="JPEG", size=(100, 100), color=(255, 0, 0)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    img.save(buf, format=format)
    return buf.getvalue()


def test_prepare_image_valid_jpeg():
    data = create_test_image(format="JPEG", size=(800, 600))
    prep = prepare_image(data)
    assert prep.width == 800
    assert prep.height == 600
    assert prep.ocr_width == 800
    assert prep.ocr_height == 600
    assert len(prep.llm_jpeg) > 0
    assert len(prep.ocr_jpeg) > 0
    assert len(prep.ocr_jpeg) <= 950 * 1024
    assert len(prep.sha256) == 64


def test_prepare_image_valid_png():
    data = create_test_image(format="PNG", size=(500, 500))
    prep = prepare_image(data)
    assert prep.width == 500
    assert prep.height == 500
    assert len(prep.llm_jpeg) > 0
    assert len(prep.ocr_jpeg) > 0


def test_prepare_image_valid_webp():
    data = create_test_image(format="WEBP", size=(400, 300))
    prep = prepare_image(data)
    assert prep.width == 400
    assert prep.height == 300


def test_prepare_image_resizes_large_dimensions():
    data = create_test_image(format="JPEG", size=(3000, 1500))
    prep = prepare_image(data)
    assert prep.width == 2000
    assert prep.height == 1000
    assert prep.ocr_width == 1600
    assert prep.ocr_height == 800


def test_prepare_image_rejects_over_36_megapixels():
    buf = io.BytesIO()
    img = Image.new("RGB", (6001, 6001), (0, 255, 0))
    img.save(buf, format="JPEG")
    data = buf.getvalue()
    with pytest.raises(InvalidImageError, match="Image exceeds 36 megapixels"):
        prepare_image(data)


def test_prepare_image_rejects_unsupported_format():
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100))
    img.save(buf, format="BMP")
    with pytest.raises(InvalidImageError, match="Unsupported image format"):
        prepare_image(buf.getvalue())


def test_prepare_image_rejects_corrupted_data():
    with pytest.raises(InvalidImageError):
        prepare_image(b"not-an-image-data")


def test_prepare_image_rejects_file_too_large(settings):
    settings.MAX_UPLOAD_MB = 1
    oversized = b"0" * (1 * 1024 * 1024 + 1)
    with pytest.raises(FileTooLargeError):
        prepare_image(oversized)
