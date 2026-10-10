import json
from unittest.mock import MagicMock, patch

import pytest
from groq import RateLimitError

from ingestion.models import ProviderCache
from ingestion.services.llm_client import (
    GroqExtractor,
    LlmRateLimitedError,
    LlmSchemaInvalidError,
    compute_llm_cache_key,
)
from ingestion.services.ocr_client import (
    OcrApiError,
    OcrSpaceClient,
    ReplayMissError,
    compute_ocr_cache_key,
    parse_ocr_response,
)


def test_ocr_coordinate_normalization():
    raw_response = {
        "ParsedResults": [
            {
                "TextOverlay": {
                    "Lines": [
                        {
                            "LineText": "Line 1",
                            "Words": [
                                {
                                    "WordText": "Line",
                                    "Left": 100,
                                    "Top": 200,
                                    "Width": 100,
                                    "Height": 50,
                                }
                            ],
                        }
                    ]
                }
            }
        ],
        "IsErroredOnProcessing": False,
    }
    result = parse_ocr_response(raw_response, ocr_width=1000, ocr_height=1000)
    assert len(result.lines) == 1
    line = result.lines[0]
    assert line.line_number == 0
    assert line.text == "Line 1"
    assert line.x_min == 0.1
    assert line.y_min == 0.2
    assert line.x_max == 0.2
    assert line.y_max == 0.25


def test_ocr_error_handling_list_and_string():
    err_list = {
        "IsErroredOnProcessing": True,
        "ErrorMessage": ["Error one", "Error two"],
    }
    with pytest.raises(OcrApiError, match="Error one; Error two"):
        parse_ocr_response(err_list, 100, 100)

    err_str = {
        "IsErroredOnProcessing": True,
        "ErrorMessage": "Single error message",
    }
    with pytest.raises(OcrApiError, match="Single error message"):
        parse_ocr_response(err_str, 100, 100)


def test_ocr_cache_key_excludes_api_key():
    key1 = compute_ocr_cache_key("test-sha", 3, "ocr_text")
    key2 = compute_ocr_cache_key("test-sha", 3, "ocr_text")
    assert key1 == key2

    client = OcrSpaceClient(api_key="secret-key-123", engine=3)
    raw_key = "ocr:test-sha:3:overlay=True:table=True:ocr_text"
    assert "secret-key-123" not in raw_key
    assert client.engine == 3
    assert "secret-key-123" not in key1


@pytest.mark.django_db
def test_ocr_record_and_replay_roundtrip():
    client = OcrSpaceClient(api_key="dummy")
    cache_id = "test-sha-roundtrip"
    cache_key = compute_ocr_cache_key(cache_id, 3, "ocr_text")

    raw_response = {
        "ParsedResults": [
            {
                "TextOverlay": {
                    "Lines": [
                        {
                            "LineText": "Cached text",
                            "Words": [],
                        }
                    ]
                }
            }
        ],
        "IsErroredOnProcessing": False,
    }
    ProviderCache.objects.create(key=cache_key, kind="ocr", response=raw_response)

    with patch("django.conf.settings.LLM_MODE", "replay"):
        result = client.read(b"dummy-bytes", 100, 100, cache_image_id=cache_id)
        assert len(result.lines) == 1
        assert result.lines[0].text == "Cached text"


@pytest.mark.django_db
def test_ocr_replay_miss_raises():
    client = OcrSpaceClient(api_key="dummy")
    with patch("django.conf.settings.LLM_MODE", "replay"):
        with pytest.raises(ReplayMissError):
            client.read(b"dummy-bytes", 100, 100, cache_image_id="missing-id")


def test_groq_rate_limit_immediate_abort_when_retry_after_too_large():
    mock_resp = MagicMock()
    mock_resp.headers = {"retry-after": "45"}

    extractor = GroqExtractor(api_key="dummy", max_retry_wait_s=20)
    with patch("django.conf.settings.LLM_MODE", "live"):
        with patch.object(
            extractor,
            "_call_groq_with_retries",
            side_effect=LlmRateLimitedError("retry-after exceeds wait limit"),
        ):
            with pytest.raises(LlmRateLimitedError, match="retry-after exceeds wait limit"):
                extractor.extract_from_text("sample")


def test_groq_rate_limit_handling_in_call_helper():
    mock_resp = MagicMock()
    mock_resp.headers = {"retry-after": "50"}
    rate_err = RateLimitError("Rate limit", response=mock_resp, body=None)

    extractor = GroqExtractor(api_key="dummy", max_retry_wait_s=20)
    with patch("ingestion.services.llm_client.Groq") as mock_groq_cls:
        mock_client = mock_groq_cls.return_value
        mock_client.chat.completions.create.side_effect = rate_err
        with pytest.raises(LlmRateLimitedError, match="retry-after exceeds wait limit"):
            extractor._call_groq_with_retries(messages=[], model="test-model")


def test_groq_schema_invalid_repair_flow():
    extractor = GroqExtractor(api_key="dummy")
    invalid_resp = {
        "choices": [{"message": {"content": '{"invalid": true}'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }

    with patch("django.conf.settings.LLM_MODE", "live"):
        with patch.object(extractor, "_call_groq_with_retries", return_value=invalid_resp):
            with patch.object(extractor, "_retry_schema_repair", return_value=invalid_resp):
                with pytest.raises(LlmSchemaInvalidError):
                    extractor.extract_from_text("hello")


@pytest.mark.django_db
def test_groq_replay_mode_roundtrip():
    extractor = GroqExtractor(api_key="dummy")
    cache_id = "test-llm-cache"
    cache_key = compute_llm_cache_key(
        cache_image_id=cache_id,
        prompt_version="extract-v3",
        model="qwen/qwen3.8-27b",
        structured_mode="json_schema_strict",
        strategy="text",
    )

    valid_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "page": {
                                "bank_name_raw": None,
                                "page_date_raw": None,
                                "has_total_row": False,
                                "total_raw": None,
                            },
                            "rows": [],
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    ProviderCache.objects.create(key=cache_key, kind="llm", response=valid_payload)

    with patch("django.conf.settings.LLM_MODE", "replay"):
        result = extractor.extract_from_text("sample", cache_image_id=cache_id, strategy="text")
        assert len(result.raw_extraction.rows) == 0
        assert result.prompt_tokens == 10


def test_groq_json_object_mode_injects_schema_and_strips_fences():
    extractor = GroqExtractor(api_key="dummy", structured_mode="json_object")
    fenced_content = (
        '```json\n{"page": {"bank_name_raw": null, "page_date_raw": null, '
        '"default_unit_raw": null, "has_total_row": false, "total_raw": null}, '
        '"rows": [{"tanggal_raw": "01/10", "date_is_repeat": false, '
        '"nama_raw": "Bu Siti", "jenis_raw": "Kardus", "berat_raw": "4,5 kg", '
        '"has_correction": false, "row_confidence": 0.95}]}\n```'
    )
    mock_resp = {
        "choices": [{"message": {"content": fenced_content}}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 40},
    }

    with patch("django.conf.settings.LLM_MODE", "live"):
        with patch.object(
            extractor, "_call_groq_with_retries", return_value=mock_resp
        ) as mock_call:
            res = extractor.extract_from_image(b"fake-bytes", strategy="vision")
            assert len(res.raw_extraction.rows) == 1
            assert res.raw_extraction.rows[0].nama_raw == "Bu Siti"
            assert res.prompt_tokens == 50
            assert res.completion_tokens == 40

            called_messages = mock_call.call_args[1]["messages"]
            system_msg = next(m["content"] for m in called_messages if m["role"] == "system")
            assert "JSON Schema:" in system_msg
            assert "Example JSON:" in system_msg
