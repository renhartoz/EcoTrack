from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.models import Nasabah, WasteType
from deposits.models import AuditLog, Deposit
from ingestion.models import ExtractedRow, Extraction, Upload
from ingestion.services.llm_client import (
    LlmRateLimitedError,
    LlmSchemaInvalidError,
    LlmTimeoutError,
)
from ingestion.services.normalize import (
    match_nasabah,
    match_waste_type,
    parse_date,
    parse_weight,
)
from ingestion.services.ocr_client import OcrApiError, ReplayMissError
from ingestion.services.preprocess import (
    FileTooLargeError,
    InvalidImageError,
    prepare_image,
)
from ingestion.services.prompts import PROMPT_VERSION, SCHEMA_VERSION
from ingestion.services.score import compute_row_score, route_row
from ingestion.services.strategies import (
    OcrTextStrategy,
    StrategyOutput,
    TextStrategy,
    VisionStrategy,
)
from ingestion.services.validate import validate_page_rows


def process_upload(upload_id: int) -> Upload:
    upload = Upload.objects.get(id=upload_id)
    upload.processing_started_at = timezone.now()
    upload.status = "processing"
    upload.save(update_fields=["processing_started_at", "status"])

    strategy_name = getattr(settings, "EXTRACTION_STRATEGY", "ocr_text")
    output: StrategyOutput | None = None

    try:
        if upload.source_type == "image":
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
            if locked_upload.source_type == "image" and strategy_name == "vision"
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

        waste_types = WasteType.objects.filter(is_active=True).prefetch_related("aliases")
        waste_type_candidates = [
            (wt.id, wt.name_id, [a.alias_normalized for a in wt.aliases.all()])
            for wt in waste_types
        ]

        active_nasabah = Nasabah.objects.filter(
            bank_sampah=locked_upload.bank_sampah,
            is_active=True,
        )
        nasabah_candidates = [(n.id, n.normalized_name) for n in active_nasabah]

        page_meta = output.raw_extraction.page
        upload_year = (
            locked_upload.created_at.year
            if locked_upload.created_at
            else timezone.now().year
        )
        previous_date = None

        row_intermediates = []
        for row_data in output.raw_extraction.rows:
            weight_kg, weight_flags = parse_weight(
                row_data.berat_raw,
                row_data.satuan_raw,
                default_unit_raw=page_meta.default_unit_raw,
            )
            date_val, date_quality, date_flags = parse_date(
                row_data.tanggal_raw,
                page_date_raw=page_meta.page_date_raw,
                upload_year=upload_year,
                date_is_repeat=row_data.date_is_repeat,
                previous_date=previous_date,
            )
            if date_val is not None:
                previous_date = date_val

            w_type_id, type_score, type_flags = match_waste_type(
                row_data.jenis_raw,
                waste_type_candidates,
                min_score=getattr(settings, "MATCH_MIN_TYPE", 0.75),
                ambiguity_margin=getattr(settings, "MATCH_AMBIGUITY_MARGIN", 0.05),
            )

            n_id, name_score, name_flags = match_nasabah(
                row_data.nama_raw,
                nasabah_candidates,
                min_score=getattr(settings, "MATCH_MIN_NASABAH", 0.85),
                ambiguity_margin=getattr(settings, "MATCH_AMBIGUITY_MARGIN", 0.05),
            )

            initial_flags = weight_flags + date_flags + type_flags + name_flags

            row_intermediates.append(
                {
                    "row_data": row_data,
                    "weight_kg": weight_kg,
                    "tanggal": date_val,
                    "date_quality": date_quality,
                    "waste_type_id": w_type_id,
                    "type_score": type_score,
                    "nasabah_id": n_id,
                    "name_score": name_score,
                    "flags": initial_flags,
                    "nama_raw": row_data.nama_raw,
                    "jenis_raw": row_data.jenis_raw,
                    "berat_raw": row_data.berat_raw,
                    "has_correction": row_data.has_correction,
                    "llm_confidence": row_data.row_confidence,
                }
            )

        validated_flags_per_row = validate_page_rows(
            row_intermediates,
            bank_id=locked_upload.bank_sampah_id,
            today=timezone.now().date(),
        )

        auto_save_enabled = getattr(settings, "AUTO_SAVE_ENABLED", False)

        for idx, inter in enumerate(row_intermediates):
            row_data = inter["row_data"]
            final_flags = validated_flags_per_row[idx]
            score = compute_row_score(
                llm_confidence=inter["llm_confidence"],
                type_score=inter["type_score"],
                name_score=inter["name_score"],
                weight_kg=inter["weight_kg"],
                date_val=inter["tanggal"],
                date_quality=inter["date_quality"],
                flags=final_flags,
            )
            route = route_row(
                score=score,
                flags=final_flags,
                auto_save_enabled=auto_save_enabled,
            )

            status = "pending"
            deposit = None

            if route == "auto" and auto_save_enabled:
                deposit = Deposit.objects.create(
                    bank_sampah=locked_upload.bank_sampah,
                    nasabah_id=inter["nasabah_id"],
                    waste_type_id=inter["waste_type_id"],
                    weight_kg=inter["weight_kg"],
                    deposit_date=inter["tanggal"],
                    source="auto",
                    upload=locked_upload,
                    created_by=None,
                )
                AuditLog.objects.create(
                    bank_sampah=locked_upload.bank_sampah,
                    actor=None,
                    actor_label="system:pipeline",
                    action="auto_save",
                    entity_type="deposit",
                    entity_id=deposit.id,
                    before={},
                    after={
                        "weight_kg": str(deposit.weight_kg),
                        "deposit_date": str(deposit.deposit_date),
                        "nasabah_id": deposit.nasabah_id,
                        "waste_type_id": deposit.waste_type_id,
                    },
                )
                status = "saved"

            ExtractedRow.objects.create(
                upload=locked_upload,
                extraction=extraction,
                row_index=row_data.row_index,
                tanggal_raw=row_data.tanggal_raw,
                nama_raw=row_data.nama_raw,
                jenis_raw=row_data.jenis_raw,
                berat_raw=row_data.berat_raw,
                satuan_raw=row_data.satuan_raw,
                evidence_text=row_data.evidence_text,
                has_correction=row_data.has_correction,
                date_is_repeat=row_data.date_is_repeat,
                llm_confidence=row_data.row_confidence,
                y_min=row_data.y_min,
                y_max=row_data.y_max,
                source_lines=row_data.source_lines,
                tanggal=inter["tanggal"],
                nasabah_id=inter["nasabah_id"],
                waste_type_id=inter["waste_type_id"],
                weight_kg=inter["weight_kg"],
                flags=final_flags,
                score=score,
                route=route,
                status=status,
                human_edited=False,
                deposit=deposit,
            )

        locked_upload.status = "ready"
        locked_upload.error_code = None
        locked_upload.error_message = None
        locked_upload.save(update_fields=["status", "error_code", "error_message"])

    return locked_upload
