from dataclasses import dataclass
from typing import Any

from ingestion.services.llm_client import ExtractionResult, GroqExtractor
from ingestion.services.ocr_client import OcrResult, OcrSpaceClient
from ingestion.services.prompts import (
    OCR_TEXT_SYSTEM_PROMPT,
    TEXT_SYSTEM_PROMPT,
    VISION_SYSTEM_PROMPT,
)
from ingestion.services.schemas import RawExtraction, RawRow, apply_post_parse_rules


@dataclass(frozen=True)
class StrategyOutput:
    raw_extraction: RawExtraction
    extraction_result: ExtractionResult
    ocr_lines: list[dict[str, Any]] | None


class BaseStrategy:
    def extract(self, **kwargs: Any) -> StrategyOutput:
        raise NotImplementedError


class VisionStrategy(BaseStrategy):
    def __init__(self, extractor: GroqExtractor | None = None):
        self.extractor = extractor or GroqExtractor()

    def extract(
        self,
        llm_jpeg: bytes,
        cache_image_id: str | None = None,
        **kwargs: Any,
    ) -> StrategyOutput:
        result = self.extractor.extract_from_image(
            jpeg_bytes=llm_jpeg,
            cache_image_id=cache_image_id,
            system_prompt=VISION_SYSTEM_PROMPT,
            strategy="vision",
        )
        cleaned = apply_post_parse_rules(result.raw_extraction)
        return StrategyOutput(
            raw_extraction=cleaned,
            extraction_result=result,
            ocr_lines=None,
        )


class OcrTextStrategy(BaseStrategy):
    def __init__(
        self,
        ocr_client: OcrSpaceClient | None = None,
        extractor: GroqExtractor | None = None,
    ):
        self.ocr_client = ocr_client or OcrSpaceClient()
        self.extractor = extractor or GroqExtractor()

    def extract(
        self,
        ocr_jpeg: bytes,
        ocr_width: int,
        ocr_height: int,
        cache_image_id: str | None = None,
        **kwargs: Any,
    ) -> StrategyOutput:
        ocr_result: OcrResult = self.ocr_client.read(
            ocr_jpeg_bytes=ocr_jpeg,
            ocr_width=ocr_width,
            ocr_height=ocr_height,
            cache_image_id=cache_image_id,
            strategy="ocr_text",
        )

        lines_text = "\n".join(f"[L{line.line_number}] {line.text}" for line in ocr_result.lines)

        result = self.extractor.extract_from_text(
            text=lines_text,
            cache_image_id=cache_image_id,
            system_prompt=OCR_TEXT_SYSTEM_PROMPT,
            strategy="ocr_text",
        )

        cleaned = apply_post_parse_rules(
            result.raw_extraction,
            num_ocr_lines=len(ocr_result.lines),
        )

        line_map = {line.line_number: line for line in ocr_result.lines}
        positioned_rows: list[RawRow] = []

        for row in cleaned.rows:
            source_lines = row.source_lines
            if source_lines:
                matched_lines = [line_map[idx] for idx in source_lines if idx in line_map]
                if matched_lines:
                    min_y = min(line.y_min for line in matched_lines)
                    max_y = max(line.y_max for line in matched_lines)
                    padded_min_y = max(0.0, min_y - 0.01)
                    padded_max_y = min(1.0, max_y + 0.01)
                    positioned_rows.append(
                        RawRow(
                            row_index=row.row_index,
                            tanggal_raw=row.tanggal_raw,
                            date_is_repeat=row.date_is_repeat,
                            nama_raw=row.nama_raw,
                            jenis_raw=row.jenis_raw,
                            berat_raw=row.berat_raw,
                            satuan_raw=row.satuan_raw,
                            evidence_text=row.evidence_text,
                            row_confidence=row.row_confidence,
                            y_min=padded_min_y,
                            y_max=padded_max_y,
                            source_lines=source_lines,
                        )
                    )
                    continue

            positioned_rows.append(
                RawRow(
                    row_index=row.row_index,
                    tanggal_raw=row.tanggal_raw,
                    date_is_repeat=row.date_is_repeat,
                    nama_raw=row.nama_raw,
                    jenis_raw=row.jenis_raw,
                    berat_raw=row.berat_raw,
                    satuan_raw=row.satuan_raw,
                    evidence_text=row.evidence_text,
                    row_confidence=row.row_confidence,
                    y_min=None,
                    y_max=None,
                    source_lines=source_lines,
                )
            )

        final_extraction = RawExtraction(
            page=cleaned.page,
            rows=positioned_rows,
        )

        serialized_lines = [
            {
                "line_number": line.line_number,
                "text": line.text,
                "y_min": line.y_min,
                "y_max": line.y_max,
                "x_min": line.x_min,
                "x_max": line.x_max,
            }
            for line in ocr_result.lines
        ]

        return StrategyOutput(
            raw_extraction=final_extraction,
            extraction_result=result,
            ocr_lines=serialized_lines,
        )


class TextStrategy(BaseStrategy):
    def __init__(self, extractor: GroqExtractor | None = None):
        self.extractor = extractor or GroqExtractor()

    def extract(
        self,
        text: str,
        cache_image_id: str | None = None,
        **kwargs: Any,
    ) -> StrategyOutput:
        result = self.extractor.extract_from_text(
            text=text,
            cache_image_id=cache_image_id,
            system_prompt=TEXT_SYSTEM_PROMPT,
            strategy="text",
        )
        cleaned = apply_post_parse_rules(result.raw_extraction)

        text_rows = [
            RawRow(
                row_index=row.row_index,
                tanggal_raw=row.tanggal_raw,
                date_is_repeat=row.date_is_repeat,
                nama_raw=row.nama_raw,
                jenis_raw=row.jenis_raw,
                berat_raw=row.berat_raw,
                satuan_raw=row.satuan_raw,
                evidence_text=row.evidence_text,
                row_confidence=row.row_confidence,
                y_min=None,
                y_max=None,
                source_lines=None,
            )
            for row in cleaned.rows
        ]

        return StrategyOutput(
            raw_extraction=RawExtraction(page=cleaned.page, rows=text_rows),
            extraction_result=result,
            ocr_lines=None,
        )
