from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ingestion.models import ExtractedRow, Extraction, Upload
from ingestion.services.llm_client import (
    LlmRateLimitedError,
    LlmSchemaInvalidError,
    LlmTimeoutError,
)
from ingestion.services.ocr_client import OcrApiError, ReplayMissError
from ingestion.services.preprocess import (
    FileTooLargeError,
    InvalidImageError,
    prepare_image,
)
from ingestion.services.prompts import PROMPT_VERSION, SCHEMA_VERSION
from ingestion.services.strategies import (
    OcrTextStrategy,
    StrategyOutput,
    TextStrategy,
    VisionStrategy,
)


def process_upload(upload_id: int) -> Upload:
    upload = Upload.objects.get(id=upload_id)
    upload.processing_started_at = timezone.now()
    upload.status = "processing"
    upload.save(update_fields=["processing_started_at", "status"])

    strategy_name = "vision"
    output: StrategyOutput | None = None

    try:
        if upload.source_type == "image":
            strategy_name = getattr(settings, "EXTRACTION_STRATEGY", "vision")
            image_data = upload.image.data
            cache_id = upload.source_sha256 or upload.image_sha256

            if strategy_name == "vision":
                output = VisionStrategy().extract(
                    llm_jpeg=image_data,
                    cache_image_id=cache_id,
                )
            elif strategy_name == "ocr_text":
                prep = prepare_image(image_data)
                output = OcrTextStrategy().extract(
                    ocr_jpeg=prep.ocr_jpeg,
                    ocr_width=prep.ocr_width,
                    ocr_height=prep.ocr_height,
                    cache_image_id=cache_id,
                )
            else:
                raise ValueError(f"Unsupported strategy: {strategy_name}")

        elif upload.source_type == "text":
            strategy_name = "text"
            output = TextStrategy().extract(
                text=upload.raw_text or "",
                cache_image_id=upload.source_sha256,
            )
        else:
            raise ValueError(f"Unknown source_type: {upload.source_type}")

    except LlmRateLimitedError as exc:
        upload.status = "failed"
        upload.error_code = "LLM_RATE_LIMITED"
        upload.error_message = str(exc)
        upload.save(update_fields=["status", "error_code", "error_message"])
        return upload

    except LlmTimeoutError as exc:
        upload.status = "failed"
        upload.error_code = "LLM_TIMEOUT"
        upload.error_message = str(exc)
        upload.save(update_fields=["status", "error_code", "error_message"])
        return upload

    except LlmSchemaInvalidError as exc:
        upload.status = "failed"
        upload.error_code = "LLM_SCHEMA_INVALID"
        upload.error_message = str(exc)
        upload.save(update_fields=["status", "error_code", "error_message"])
        return upload

    except OcrApiError as exc:
        upload.status = "failed"
        upload.error_code = "OCR_API_ERROR"
        upload.error_message = str(exc)
        upload.save(update_fields=["status", "error_code", "error_message"])
        return upload

    except ReplayMissError as exc:
        upload.status = "failed"
        upload.error_code = "REPLAY_MISS"
        upload.error_message = str(exc)
        upload.save(update_fields=["status", "error_code", "error_message"])
        return upload

    except (InvalidImageError, FileTooLargeError) as exc:
        upload.status = "failed"
        upload.error_code = (
            "INVALID_IMAGE" if isinstance(exc, InvalidImageError) else "FILE_TOO_LARGE"
        )
        upload.error_message = str(exc)
        upload.save(update_fields=["status", "error_code", "error_message"])
        return upload

    except Exception as exc:
        upload.status = "failed"
        upload.error_code = "LLM_API_ERROR"
        upload.error_message = str(exc)
        upload.save(update_fields=["status", "error_code", "error_message"])
        return upload

    with transaction.atomic():
        locked_upload = Upload.objects.select_for_update().get(id=upload_id)
        locked_upload.rows.filter(status="pending").delete()

        model_name = (
            getattr(settings, "GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
            if locked_upload.source_type == "image"
            else getattr(settings, "GROQ_TEXT_MODEL", "qwen/qwen3.8-27b")
        )
        ocr_engine_val = (
            str(getattr(settings, "OCR_SPACE_ENGINE", 3)) if strategy_name == "ocr_text" else None
        )

        extraction = Extraction.objects.create(
            upload=locked_upload,
            strategy=strategy_name,
            provider="groq",
            model=model_name,
            ocr_engine=ocr_engine_val,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            raw_response=output.extraction_result.raw_response,
            ocr_lines=output.ocr_lines,
            page_meta=output.raw_extraction.page.model_dump(),
            latency_ms=output.extraction_result.latency_ms,
            input_tokens=output.extraction_result.prompt_tokens,
            output_tokens=output.extraction_result.completion_tokens,
            from_cache=getattr(settings, "LLM_MODE", "live") == "replay",
        )

        rows = [
            ExtractedRow(
                upload=locked_upload,
                extraction=extraction,
                row_index=row_data.row_index,
                tanggal_raw=row_data.tanggal_raw,
                nama_raw=row_data.nama_raw,
                jenis_raw=row_data.jenis_raw,
                berat_raw=row_data.berat_raw,
                satuan_raw=row_data.satuan_raw,
                evidence_text=row_data.evidence_text,
                date_is_repeat=row_data.date_is_repeat,
                llm_confidence=row_data.row_confidence,
                y_min=row_data.y_min,
                y_max=row_data.y_max,
                source_lines=row_data.source_lines,
                status="pending",
            )
            for row_data in output.raw_extraction.rows
        ]
        ExtractedRow.objects.bulk_create(rows)

        locked_upload.status = "ready"
        locked_upload.error_code = None
        locked_upload.error_message = None
        locked_upload.save(update_fields=["status", "error_code", "error_message"])

    return locked_upload
