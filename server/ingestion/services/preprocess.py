import hashlib
import io
from dataclasses import dataclass

from django.conf import settings
from PIL import Image, ImageOps


class PreprocessError(Exception):
    pass


class FileTooLargeError(PreprocessError):
    pass


class InvalidImageError(PreprocessError):
    pass


@dataclass(frozen=True)
class PreparedImage:
    llm_jpeg: bytes
    ocr_jpeg: bytes
    width: int
    height: int
    ocr_width: int
    ocr_height: int
    sha256: str


def prepare_image(file_or_bytes: bytes | io.BytesIO | object) -> PreparedImage:
    max_upload_mb = getattr(settings, "MAX_UPLOAD_MB", 4)
    max_bytes = max_upload_mb * 1024 * 1024

    if hasattr(file_or_bytes, "read"):
        raw_bytes = file_or_bytes.read()
    elif isinstance(file_or_bytes, bytes):
        raw_bytes = file_or_bytes
    else:
        raise InvalidImageError("Invalid input type")

    if len(raw_bytes) > max_bytes:
        raise FileTooLargeError("File exceeds maximum allowed size")

    try:
        header_image = Image.open(io.BytesIO(raw_bytes))
        image_format = (header_image.format or "").upper()
        if image_format not in ("JPEG", "PNG", "WEBP"):
            raise InvalidImageError("Unsupported image format")
        if header_image.width * header_image.height > 36_000_000:
            raise InvalidImageError("Image exceeds 36 megapixels")
        header_image.verify()
    except (InvalidImageError, FileTooLargeError):
        raise
    except Exception as exc:
        raise InvalidImageError("Failed to verify image") from exc

    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
    except Exception as exc:
        raise InvalidImageError("Failed to decode image") from exc

    width, height = image.size
    long_edge = max(width, height)
    if long_edge > 2000:
        scale = 2000 / long_edge
        new_width = max(1, int(round(width * scale)))
        new_height = max(1, int(round(height * scale)))
        llm_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    else:
        llm_image = image

    llm_buf = io.BytesIO()
    llm_image.save(llm_buf, format="JPEG", quality=85)
    llm_jpeg = llm_buf.getvalue()
    llm_sha256 = hashlib.sha256(llm_jpeg).hexdigest()
    llm_w, llm_h = llm_image.size

    max_ocr_bytes = 950 * 1024
    if long_edge > 1600:
        scale = 1600 / long_edge
        target_w = max(1, int(round(width * scale)))
        target_h = max(1, int(round(height * scale)))
        ocr_image = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
    else:
        ocr_image = image

    ocr_jpeg = b""
    quality_steps = (85, 75, 65, 55)

    for q in quality_steps:
        buf = io.BytesIO()
        ocr_image.save(buf, format="JPEG", quality=q)
        data = buf.getvalue()
        if len(data) <= max_ocr_bytes:
            ocr_jpeg = data
            break

    while len(ocr_jpeg) == 0 or len(ocr_jpeg) > max_ocr_bytes:
        cur_w, cur_h = ocr_image.size
        new_w = max(1, int(round(cur_w * 0.9)))
        new_h = max(1, int(round(cur_h * 0.9)))
        if new_w == cur_w and new_h == cur_h:
            break
        ocr_image = ocr_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        ocr_image.save(buf, format="JPEG", quality=55)
        ocr_jpeg = buf.getvalue()

    return PreparedImage(
        llm_jpeg=llm_jpeg,
        ocr_jpeg=ocr_jpeg,
        width=llm_w,
        height=llm_h,
        ocr_width=ocr_image.width,
        ocr_height=ocr_image.height,
        sha256=llm_sha256,
    )
