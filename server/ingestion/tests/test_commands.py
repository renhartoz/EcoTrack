import io
import json
from unittest.mock import MagicMock

import httpx
import pytest
from django.core.management import CommandError, call_command
from groq import RateLimitError
from PIL import Image

from ingestion.services.schemas import PageMeta, RawExtraction, RawRow


def test_probe_providers_missing_file():
    with pytest.raises(CommandError, match="Image file not found"):
        call_command("probe_providers", "--image", "non_existent_file.jpg")


def test_probe_providers_skipped_when_keys_blank(tmp_path):
    img_path = tmp_path / "sample.jpg"
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    img.save(str(img_path), format="JPEG")

    out = io.StringIO()
    save_dir = tmp_path / "probe_output"
    call_command(
        "probe_providers",
        "--image",
        str(img_path),
        "--save-dir",
        str(save_dir),
        "--no-wait",
        stdout=out,
    )
    output = out.getvalue()
    assert "EcoTrack Provider Probe" in output
    assert "SKIPPED: GROQ_API_KEY is not configured" in output
    assert "SKIPPED: OCR_SPACE_API_KEY is not configured" in output
    assert save_dir.exists()


def test_probe_providers_groq_success(tmp_path, monkeypatch):
    img_path = tmp_path / "sample.jpg"
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    img.save(str(img_path), format="JPEG")

    raw_payload = RawExtraction(
        page=PageMeta(bank_name_raw="Test Bank"),
        rows=[
            RawRow(
                row_index=1,
                tanggal_raw="2026-03-01",
                nama_raw="Budi",
                jenis_raw="Kardus",
                berat_raw="2.5",
                satuan_raw="kg",
                row_confidence=0.95,
                y_min=0.1,
                y_max=0.2,
            )
        ],
    ).model_dump_json()

    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = raw_payload
    mock_completion.choices = [mock_choice]
    mock_completion.usage.prompt_tokens = 120
    mock_completion.usage.completion_tokens = 45
    mock_completion.usage.total_tokens = 165

    mock_raw_res = MagicMock()
    mock_raw_res.parse.return_value = mock_completion
    mock_raw_res.headers = {
        "x-ratelimit-remaining-tokens": "5000",
        "retry-after": "0",
    }

    mock_client = MagicMock()
    mock_client.chat.completions.with_raw_response.create.return_value = mock_raw_res

    monkeypatch.setattr(
        "ingestion.management.commands.probe_providers.Groq",
        lambda **_: mock_client,
    )
    monkeypatch.setattr("django.conf.settings.GROQ_API_KEY", "dummy-groq-key")

    save_dir = tmp_path / "probe_results"
    out = io.StringIO()
    call_command(
        "probe_providers",
        "--image",
        str(img_path),
        "--save-dir",
        str(save_dir),
        "--no-wait",
        stdout=out,
    )
    output = out.getvalue()
    assert "STATUS: PASS" in output
    assert "index | tanggal_raw" in output
    assert "Budi" in output
    assert "Kardus" in output
    assert "Output token count: 45" in output

    saved_file = save_dir / "groq_json_schema_strict.json"
    assert saved_file.exists()
    with open(saved_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data["request_parameters"]["max_completion_tokens"] == 3000
    assert data["request_parameters"]["response_format_type"] == "json_schema"
    assert "apikey" not in data["request_parameters"]
    assert "api_key" not in data["request_parameters"]
    assert "dummy-groq-key" not in json.dumps(data)
    assert data["rate_limit_headers"]["x-ratelimit-remaining-tokens"] == "5000"
    assert len(data["rows"]) == 1


def test_probe_providers_ocr_success(tmp_path, monkeypatch):
    img_path = tmp_path / "sample.jpg"
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    img.save(str(img_path), format="JPEG")

    ocr_response_data = {
        "ParsedResults": [
            {
                "TextOverlay": {
                    "Lines": [
                        {
                            "LineText": "Header Row Text",
                            "Words": [
                                {
                                    "WordText": "Header",
                                    "Left": 10,
                                    "Top": 20,
                                    "Width": 30,
                                    "Height": 10,
                                }
                            ],
                            "MinTop": 20,
                            "MaxHeight": 10,
                        }
                    ]
                }
            }
        ],
        "OCRExitCode": 1,
        "IsErroredOnProcessing": False,
        "ProcessingTimeInMilliseconds": "350",
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = ocr_response_data

    monkeypatch.setattr("requests.post", lambda *_, **__: mock_resp)
    monkeypatch.setattr("django.conf.settings.OCR_SPACE_API_KEY", "dummy-ocr-key")

    save_dir = tmp_path / "probe_results"
    out = io.StringIO()
    call_command(
        "probe_providers",
        "--image",
        str(img_path),
        "--save-dir",
        str(save_dir),
        "--no-wait",
        stdout=out,
    )
    output = out.getvalue()
    assert "Overlay Lines recognized: 1" in output
    assert "First 25 OCR Lines" in output
    assert "Header Row Text" in output

    saved_file = save_dir / "ocr_engine_2.json"
    assert saved_file.exists()
    with open(saved_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data["request_parameters"]["isTable"] == "true"
    assert "apikey" not in data["request_parameters"]
    assert "dummy-ocr-key" not in json.dumps(data)
    assert len(data["lines"]) == 1


def test_probe_providers_groq_429(tmp_path, monkeypatch):
    img_path = tmp_path / "sample.jpg"
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    img.save(str(img_path), format="JPEG")

    http_req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    http_resp = httpx.Response(
        status_code=429,
        headers={"retry-after": "65", "x-ratelimit-remaining-tokens": "0"},
        request=http_req,
    )
    mock_client = MagicMock()
    mock_client.chat.completions.with_raw_response.create.side_effect = RateLimitError(
        message="rate_limit_exceeded",
        response=http_resp,
        body=None,
    )

    monkeypatch.setattr(
        "ingestion.management.commands.probe_providers.Groq",
        lambda **_: mock_client,
    )
    monkeypatch.setattr("django.conf.settings.GROQ_API_KEY", "dummy-groq-key")

    save_dir = tmp_path / "probe_results"
    out = io.StringIO()
    call_command(
        "probe_providers",
        "--image",
        str(img_path),
        "--save-dir",
        str(save_dir),
        "--no-wait",
        stdout=out,
    )
    output = out.getvalue()
    assert "STATUS: FAIL (429 Rate Limited" in output
    assert "max_completion_tokens sent: 3000" in output
    assert "Full error text: rate_limit_exceeded" in output

    err_file = save_dir / "groq_json_schema_strict_error.json"
    assert err_file.exists()
    with open(err_file, encoding="utf-8") as f:
        err_data = json.load(f)
    assert err_data["request_parameters"]["max_completion_tokens"] == 3000
    assert "dummy-groq-key" not in json.dumps(err_data)
