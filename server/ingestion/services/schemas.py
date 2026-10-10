import re
from typing import Any

from pydantic import BaseModel, ConfigDict


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PageMeta(WireModel):
    bank_name_raw: str | None = None
    page_date_raw: str | None = None
    default_unit_raw: str | None = None
    has_total_row: bool = False
    total_raw: str | None = None


class VisionRow(WireModel):
    tanggal_raw: str | None = None
    date_is_repeat: bool = False
    nama_raw: str | None = None
    jenis_raw: str | None = None
    berat_raw: str | None = None
    has_correction: bool = False
    row_confidence: float = 0.0


class OcrTextRow(WireModel):
    tanggal_raw: str | None = None
    date_is_repeat: bool = False
    nama_raw: str | None = None
    jenis_raw: str | None = None
    berat_raw: str | None = None
    row_confidence: float = 0.0
    source_lines: list[int] = []


class TextRow(WireModel):
    tanggal_raw: str | None = None
    date_is_repeat: bool = False
    nama_raw: str | None = None
    jenis_raw: str | None = None
    berat_raw: str | None = None
    row_confidence: float = 0.0
    evidence_text: str = ""


class VisionExtraction(WireModel):
    page: PageMeta
    rows: list[VisionRow]


class OcrTextExtraction(WireModel):
    page: PageMeta
    rows: list[OcrTextRow]


class TextExtraction(WireModel):
    page: PageMeta
    rows: list[TextRow]


class RawRow(WireModel):
    row_index: int = 0
    tanggal_raw: str | None = None
    date_is_repeat: bool = False
    nama_raw: str | None = None
    jenis_raw: str | None = None
    berat_raw: str | None = None
    satuan_raw: str | None = None
    evidence_text: str = ""
    has_correction: bool = False
    row_confidence: float = 0.0
    y_min: float | None = None
    y_max: float | None = None
    source_lines: list[int] | None = None


class RawExtraction(WireModel):
    page: PageMeta
    rows: list[RawRow]


def vision_row_to_raw(row: VisionRow, idx: int) -> RawRow:
    evidence_parts = [p for p in [row.tanggal_raw, row.nama_raw, row.jenis_raw, row.berat_raw] if p]
    evidence = " ".join(evidence_parts)
    return RawRow(
        row_index=idx,
        tanggal_raw=row.tanggal_raw,
        date_is_repeat=row.date_is_repeat,
        nama_raw=row.nama_raw,
        jenis_raw=row.jenis_raw,
        berat_raw=row.berat_raw,
        satuan_raw=None,
        evidence_text=evidence,
        has_correction=row.has_correction,
        row_confidence=row.row_confidence,
        y_min=None,
        y_max=None,
        source_lines=None,
    )


def ocr_text_row_to_raw(row: OcrTextRow, idx: int) -> RawRow:
    return RawRow(
        row_index=idx,
        tanggal_raw=row.tanggal_raw,
        date_is_repeat=row.date_is_repeat,
        nama_raw=row.nama_raw,
        jenis_raw=row.jenis_raw,
        berat_raw=row.berat_raw,
        satuan_raw=None,
        evidence_text="",
        has_correction=False,
        row_confidence=row.row_confidence,
        y_min=None,
        y_max=None,
        source_lines=row.source_lines,
    )


def text_row_to_raw(row: TextRow, idx: int) -> RawRow:
    return RawRow(
        row_index=idx,
        tanggal_raw=row.tanggal_raw,
        date_is_repeat=row.date_is_repeat,
        nama_raw=row.nama_raw,
        jenis_raw=row.jenis_raw,
        berat_raw=row.berat_raw,
        satuan_raw=None,
        evidence_text=row.evidence_text,
        has_correction=False,
        row_confidence=row.row_confidence,
        y_min=None,
        y_max=None,
        source_lines=None,
    )


def clean_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def apply_post_parse_rules(
    raw: RawExtraction,
    num_ocr_lines: int | None = None,
) -> RawExtraction:
    cleaned_rows: list[RawRow] = []

    for idx, row in enumerate(raw.rows):
        confidence = max(0.0, min(1.0, float(row.row_confidence)))

        y_min = row.y_min
        y_max = row.y_max
        if y_min is not None and y_max is not None:
            if not (0.0 <= y_min < y_max <= 1.0):
                y_min = None
                y_max = None
        else:
            y_min = None
            y_max = None

        source_lines = row.source_lines
        if source_lines is not None and num_ocr_lines is not None:
            source_lines = [
                line_idx
                for line_idx in source_lines
                if isinstance(line_idx, int) and 0 <= line_idx < num_ocr_lines
            ]

        cleaned_rows.append(
            RawRow(
                row_index=idx,
                tanggal_raw=row.tanggal_raw,
                date_is_repeat=row.date_is_repeat,
                nama_raw=row.nama_raw,
                jenis_raw=row.jenis_raw,
                berat_raw=row.berat_raw,
                satuan_raw=row.satuan_raw,
                evidence_text=row.evidence_text,
                has_correction=row.has_correction,
                row_confidence=confidence,
                y_min=y_min,
                y_max=y_max,
                source_lines=source_lines,
            )
        )

    return RawExtraction(
        page=raw.page,
        rows=cleaned_rows,
    )


def get_strict_json_schema(model_cls: type[BaseModel] = VisionExtraction) -> dict[str, Any]:
    schema = model_cls.model_json_schema()

    def enforce_strict(obj: Any) -> Any:
        if isinstance(obj, dict):
            new_obj = {}
            for k, v in obj.items():
                new_obj[k] = enforce_strict(v)
            if new_obj.get("type") == "object":
                new_obj["additionalProperties"] = False
                if "properties" in new_obj and "required" not in new_obj:
                    new_obj["required"] = list(new_obj["properties"].keys())
            return new_obj
        if isinstance(obj, list):
            return [enforce_strict(item) for item in obj]
        return obj

    return enforce_strict(schema)
