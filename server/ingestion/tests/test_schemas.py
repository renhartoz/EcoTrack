import pytest
from pydantic import ValidationError

from ingestion.services.schemas import (
    PageMeta,
    RawExtraction,
    RawRow,
    apply_post_parse_rules,
    clean_json_text,
    get_strict_json_schema,
)


def test_raw_extraction_model_valid():
    payload = {
        "page": {
            "bank_name_raw": "Bank Sampah Bersih",
            "page_date_raw": "Sep 2026",
            "has_total_row": False,
            "total_raw": None,
        },
        "rows": [
            {
                "row_index": 5,
                "tanggal_raw": "12/9",
                "date_is_repeat": False,
                "nama_raw": "Bu Siti",
                "jenis_raw": "botol",
                "berat_raw": "2,5",
                "satuan_raw": "kg",
                "evidence_text": "12/9 Bu Siti botol 2,5 kg",
                "row_confidence": 0.85,
                "y_min": 0.3,
                "y_max": 0.4,
                "source_lines": None,
            }
        ],
    }
    parsed = RawExtraction.model_validate(payload)
    assert parsed.page.bank_name_raw == "Bank Sampah Bersih"
    assert len(parsed.rows) == 1
    assert parsed.rows[0].nama_raw == "Bu Siti"


def test_raw_extraction_forbids_extra_fields():
    payload = {
        "page": {
            "bank_name_raw": None,
            "page_date_raw": None,
            "has_total_row": False,
            "total_raw": None,
            "extra_field": 123,
        },
        "rows": [],
    }
    with pytest.raises(ValidationError):
        RawExtraction.model_validate(payload)


def test_apply_post_parse_rules_renumbers_and_clips():
    raw = RawExtraction(
        page=PageMeta(),
        rows=[
            RawRow(
                row_index=99,
                nama_raw="First",
                row_confidence=1.8,
                y_min=0.1,
                y_max=0.2,
            ),
            RawRow(
                row_index=12,
                nama_raw="Second",
                row_confidence=-0.5,
                y_min=0.5,
                y_max=0.3,
            ),
            RawRow(
                row_index=55,
                nama_raw="Third",
                row_confidence=0.7,
                y_min=-0.1,
                y_max=0.9,
            ),
            RawRow(
                row_index=3,
                nama_raw="Fourth",
                row_confidence=0.9,
                y_min=0.2,
                y_max=1.2,
            ),
        ],
    )
    cleaned = apply_post_parse_rules(raw)
    assert cleaned.rows[0].row_index == 0
    assert cleaned.rows[0].row_confidence == 1.0
    assert cleaned.rows[0].y_min == 0.1
    assert cleaned.rows[0].y_max == 0.2

    assert cleaned.rows[1].row_index == 1
    assert cleaned.rows[1].row_confidence == 0.0
    assert cleaned.rows[1].y_min is None
    assert cleaned.rows[1].y_max is None

    assert cleaned.rows[2].row_index == 2
    assert cleaned.rows[2].y_min is None
    assert cleaned.rows[2].y_max is None

    assert cleaned.rows[3].row_index == 3
    assert cleaned.rows[3].y_min is None
    assert cleaned.rows[3].y_max is None


def test_apply_post_parse_rules_source_lines_filter():
    raw = RawExtraction(
        page=PageMeta(),
        rows=[
            RawRow(
                row_index=0,
                source_lines=[0, 1, 5, -1, 10],
            )
        ],
    )
    cleaned = apply_post_parse_rules(raw, num_ocr_lines=5)
    assert cleaned.rows[0].source_lines == [0, 1]


def test_clean_json_text_markdown_fences():
    fenced = '```json\n{"page": {}, "rows": []}\n```'
    cleaned = clean_json_text(fenced)
    assert cleaned == '{"page": {}, "rows": []}'

    raw = '{"page": {}, "rows": []}'
    assert clean_json_text(raw) == raw


def test_get_strict_json_schema():
    schema = get_strict_json_schema()
    assert schema["additionalProperties"] is False
    assert "properties" in schema
    assert "rows" in schema["required"]
