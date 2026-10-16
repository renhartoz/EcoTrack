import re
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from ingestion.services.llm_client import ExtractionResult, GroqExtractor
from ingestion.services.normalize import fuzz, normalize_text
from ingestion.services.ocr_client import OcrLine, OcrResult, OcrSpaceClient
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
    extra_flags_by_row: dict[int, list[dict[str, str]]] | None = None


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
                            has_correction=row.has_correction,
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
                    has_correction=row.has_correction,
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

        combined_result = ExtractionResult(
            raw_extraction=result.raw_extraction,
            raw_response=result.raw_response,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=result.latency_ms + ocr_result.latency_ms,
        )

        return StrategyOutput(
            raw_extraction=final_extraction,
            extraction_result=combined_result,
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
                has_correction=row.has_correction,
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


def group_ocr_lines_into_rows(lines: list[OcrLine]) -> list[list[OcrLine]]:
    if not lines:
        return []
    grouped: list[list[OcrLine]] = []
    current_row: list[OcrLine] = []
    prev_x_min = -1.0
    for line in lines:
        if current_row and line.x_min < prev_x_min - 0.15:
            grouped.append(current_row)
            current_row = [line]
        else:
            current_row.append(line)
        prev_x_min = line.x_min
    if current_row:
        grouped.append(current_row)
    return [row for row in grouped if len(row) >= 3]


def _digits_only(val: str | None) -> list[str]:
    if not val:
        return []
    raw_nums = re.findall(r"\d+(?:[.,]\d+)*", val)
    cleaned = []
    for n in raw_nums:
        d = re.sub(r"[.,]", "", n).lstrip("0") or "0"
        cleaned.append(d)
    return cleaned


class HybridStrategy(BaseStrategy):
    def __init__(
        self,
        ocr_client: OcrSpaceClient | None = None,
        extractor: GroqExtractor | None = None,
    ):
        self.ocr_client = ocr_client or OcrSpaceClient()
        self.extractor = extractor or GroqExtractor()

    def extract(
        self,
        llm_jpeg: bytes,
        ocr_jpeg: bytes,
        ocr_width: int,
        ocr_height: int,
        cache_image_id: str | None = None,
        **kwargs: Any,
    ) -> StrategyOutput:
        vision_res = self.extractor.extract_from_image(
            jpeg_bytes=llm_jpeg,
            cache_image_id=cache_image_id,
            system_prompt=VISION_SYSTEM_PROMPT,
            strategy="vision",
        )
        cleaned = apply_post_parse_rules(vision_res.raw_extraction)

        try:
            ocr_result = self.ocr_client.read(
                ocr_jpeg_bytes=ocr_jpeg,
                ocr_width=ocr_width,
                ocr_height=ocr_height,
                cache_image_id=cache_image_id,
                strategy="ocr_text",
            )
        except Exception:
            return StrategyOutput(
                raw_extraction=cleaned,
                extraction_result=vision_res,
                ocr_lines=None,
                extra_flags_by_row={},
            )

        ocr_rows = group_ocr_lines_into_rows(ocr_result.lines)
        enable_crosscheck = getattr(settings, "ENABLE_OCR_CROSSCHECK", True)
        positioned_rows: list[RawRow] = []
        extra_flags_by_row: dict[int, list[dict[str, str]]] = {}
        used_ocr_indices: set[int] = set()

        for v_row in cleaned.rows:
            v_query = normalize_text(f"{v_row.nama_raw or ''} {v_row.jenis_raw or ''}")
            best_idx = -1
            best_sim = 0.0
            for idx, o_cells in enumerate(ocr_rows):
                if idx in used_ocr_indices:
                    continue
                o_text = normalize_text(" ".join(c.text for c in o_cells))
                if not v_query or not o_text:
                    continue
                sim = float(fuzz.WRatio(v_query, o_text)) / 100.0
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx

            row_flags: list[dict[str, str]] = []
            has_corr = v_row.has_correction

            if best_idx >= 0 and best_sim >= 0.60:
                used_ocr_indices.add(best_idx)
                matched_cells = ocr_rows[best_idx]
                min_y = max(0.0, min(c.y_min for c in matched_cells) - 0.01)
                max_y = min(1.0, max(c.y_max for c in matched_cells) + 0.01)
                ev_text = " ".join(c.text for c in matched_cells)
                src_lines = [c.line_number for c in matched_cells]

                if enable_crosscheck:
                    num_cells = [c for c in matched_cells[2:] if re.search(r"\d", c.text)]
                    if num_cells:
                        w_cell = num_cells[0]
                        ocr_nums = _digits_only(w_cell.text)
                        if len(ocr_nums) >= 2:
                            has_corr = True
                            row_flags.append({"code": "CORRECTION_PRESENT", "severity": "soft"})
                        vis_nums = _digits_only(v_row.berat_raw)
                        if vis_nums and ocr_nums:
                            if not any(vn in ocr_nums for vn in vis_nums):
                                row_flags.append(
                                    {"code": "WEIGHT_READER_MISMATCH", "severity": "soft"}
                                )

                positioned_rows.append(
                    RawRow(
                        row_index=v_row.row_index,
                        tanggal_raw=v_row.tanggal_raw,
                        date_is_repeat=v_row.date_is_repeat,
                        nama_raw=v_row.nama_raw,
                        jenis_raw=v_row.jenis_raw,
                        berat_raw=v_row.berat_raw,
                        satuan_raw=v_row.satuan_raw,
                        evidence_text=ev_text,
                        has_correction=has_corr,
                        row_confidence=v_row.row_confidence,
                        y_min=min_y,
                        y_max=max_y,
                        source_lines=src_lines,
                    )
                )
            else:
                ev_fallback = " ".join(
                    str(x)
                    for x in [
                        v_row.tanggal_raw,
                        v_row.nama_raw,
                        v_row.jenis_raw,
                        v_row.berat_raw,
                    ]
                    if x
                )
                positioned_rows.append(
                    RawRow(
                        row_index=v_row.row_index,
                        tanggal_raw=v_row.tanggal_raw,
                        date_is_repeat=v_row.date_is_repeat,
                        nama_raw=v_row.nama_raw,
                        jenis_raw=v_row.jenis_raw,
                        berat_raw=v_row.berat_raw,
                        satuan_raw=v_row.satuan_raw,
                        evidence_text=ev_fallback,
                        has_correction=has_corr,
                        row_confidence=v_row.row_confidence,
                        y_min=None,
                        y_max=None,
                        source_lines=None,
                    )
                )

            if row_flags:
                extra_flags_by_row[v_row.row_index] = row_flags

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

        combined_vision_res = ExtractionResult(
            raw_extraction=vision_res.raw_extraction,
            raw_response=vision_res.raw_response,
            prompt_tokens=vision_res.prompt_tokens,
            completion_tokens=vision_res.completion_tokens,
            latency_ms=vision_res.latency_ms + ocr_result.latency_ms,
        )

        return StrategyOutput(
            raw_extraction=RawExtraction(page=cleaned.page, rows=positioned_rows),
            extraction_result=combined_vision_res,
            ocr_lines=serialized_lines,
            extra_flags_by_row=extra_flags_by_row,
        )
