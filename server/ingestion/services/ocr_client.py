import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from django.conf import settings

from ingestion.models import ProviderCache


class OcrApiError(Exception):
    pass


class ReplayMissError(Exception):
    pass


@dataclass(frozen=True)
class OcrWord:
    text: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass(frozen=True)
class OcrLine:
    line_number: int
    text: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    words: list[OcrWord]


@dataclass(frozen=True)
class OcrResult:
    lines: list[OcrLine]
    raw_response: dict[str, Any]
    ocr_width: int
    ocr_height: int


def compute_ocr_cache_key(
    cache_image_id: str,
    ocr_engine: int | str,
    strategy: str,
) -> str:
    raw_key = f"ocr:{cache_image_id}:{ocr_engine}:overlay=True:table=True:{strategy}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def parse_ocr_response(
    raw_response: dict[str, Any],
    ocr_width: int,
    ocr_height: int,
) -> OcrResult:
    if raw_response.get("IsErroredOnProcessing") is True:
        error_msg = raw_response.get("ErrorMessage")
        if isinstance(error_msg, list):
            message = "; ".join(str(m) for m in error_msg)
        else:
            message = str(error_msg or "OCR processing failed")
        raise OcrApiError(message)

    if "lines" in raw_response:
        lines = [
            OcrLine(
                line_number=int(line_data.get("line_number", idx)),
                text=str(line_data.get("text", "")),
                x_min=float(line_data.get("x_min", 0.0)),
                y_min=float(line_data.get("y_min", 0.0)),
                x_max=float(line_data.get("x_max", 1.0)),
                y_max=float(line_data.get("y_max", 1.0)),
                words=[
                    OcrWord(
                        text=str(w.get("text", "")),
                        x_min=float(w.get("x_min", 0.0)),
                        y_min=float(w.get("y_min", 0.0)),
                        x_max=float(w.get("x_max", 1.0)),
                        y_max=float(w.get("y_max", 1.0)),
                    )
                    for w in line_data.get("words", [])
                ],
            )
            for idx, line_data in enumerate(raw_response.get("lines", []))
        ]
        return OcrResult(
            lines=lines,
            raw_response=raw_response,
            ocr_width=ocr_width,
            ocr_height=ocr_height,
        )

    parsed_results = raw_response.get("ParsedResults") or []
    if not parsed_results:
        return OcrResult(
            lines=[],
            raw_response=raw_response,
            ocr_width=ocr_width,
            ocr_height=ocr_height,
        )

    text_overlay = parsed_results[0].get("TextOverlay") or {}
    raw_lines = text_overlay.get("Lines") or []
    lines: list[OcrLine] = []

    width_float = float(max(1, ocr_width))
    height_float = float(max(1, ocr_height))

    for line_idx, line_data in enumerate(raw_lines):
        line_text = str(line_data.get("LineText") or "")
        raw_words = line_data.get("Words") or []
        words: list[OcrWord] = []

        line_x_min = 1.0
        line_y_min = 1.0
        line_x_max = 0.0
        line_y_max = 0.0

        for word_data in raw_words:
            w_text = str(word_data.get("WordText") or "")
            w_left = float(word_data.get("Left") or 0.0)
            w_top = float(word_data.get("Top") or 0.0)
            w_width = float(word_data.get("Width") or 0.0)
            w_height = float(word_data.get("Height") or 0.0)

            x_min = max(0.0, min(1.0, w_left / width_float))
            y_min = max(0.0, min(1.0, w_top / height_float))
            x_max = max(0.0, min(1.0, (w_left + w_width) / width_float))
            y_max = max(0.0, min(1.0, (w_top + w_height) / height_float))

            words.append(
                OcrWord(
                    text=w_text,
                    x_min=x_min,
                    y_min=y_min,
                    x_max=x_max,
                    y_max=y_max,
                )
            )

            line_x_min = min(line_x_min, x_min)
            line_y_min = min(line_y_min, y_min)
            line_x_max = max(line_x_max, x_max)
            line_y_max = max(line_y_max, y_max)

        if not words:
            line_x_min = 0.0
            line_y_min = 0.0
            line_x_max = 1.0
            line_y_max = 1.0

        lines.append(
            OcrLine(
                line_number=line_idx,
                text=line_text,
                x_min=line_x_min,
                y_min=line_y_min,
                x_max=line_x_max,
                y_max=line_y_max,
                words=words,
            )
        )

    return OcrResult(
        lines=lines,
        raw_response=raw_response,
        ocr_width=ocr_width,
        ocr_height=ocr_height,
    )


class OcrSpaceClient:
    def __init__(
        self,
        api_key: str | None = None,
        engine: int | str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = (
            api_key if api_key is not None else getattr(settings, "OCR_SPACE_API_KEY", "")
        )
        self.engine = engine if engine is not None else getattr(settings, "OCR_SPACE_ENGINE", 3)
        self.timeout = (
            timeout if timeout is not None else getattr(settings, "OCR_SPACE_TIMEOUT_S", 30)
        )

    def read(
        self,
        ocr_jpeg_bytes: bytes,
        ocr_width: int,
        ocr_height: int,
        cache_image_id: str | None = None,
        strategy: str = "ocr_text",
    ) -> OcrResult:
        mode = getattr(settings, "LLM_MODE", "live")
        cache_id = cache_image_id or hashlib.sha256(ocr_jpeg_bytes).hexdigest()
        cache_key = compute_ocr_cache_key(cache_id, self.engine, strategy)

        if mode == "fake":
            fixture_path = (
                Path(__file__).resolve().parent.parent
                / "tests"
                / "fixtures"
                / "ocr_space_valid.json"
            )
            with open(fixture_path, encoding="utf-8") as f:
                raw_response = json.load(f)
            return parse_ocr_response(raw_response, ocr_width, ocr_height)

        if mode == "replay":
            cached = ProviderCache.objects.filter(key=cache_key, kind="ocr").first()
            if not cached:
                raise ReplayMissError("Replay miss for OCR cache key")
            return parse_ocr_response(cached.response, ocr_width, ocr_height)

        try:
            url = "https://api.ocr.space/parse/image"
            data = {
                "apikey": self.api_key,
                "OCREngine": str(self.engine),
                "isOverlayRequired": "true",
                "isTable": "true",
                "detectOrientation": "true",
                "scale": "true",
                "language": "eng",
            }
            files = {
                "file": ("ocr.jpg", ocr_jpeg_bytes, "image/jpeg"),
            }
            response = requests.post(url, data=data, files=files, timeout=self.timeout)
        except Exception as exc:
            raise OcrApiError("OCR request failed") from exc

        if response.status_code != 200:
            raise OcrApiError(f"OCR HTTP error status {response.status_code}")

        try:
            raw_response = response.json()
        except Exception as exc:
            raise OcrApiError("Failed to parse OCR JSON response") from exc

        if mode == "record":
            ProviderCache.objects.update_or_create(
                key=cache_key,
                defaults={"kind": "ocr", "response": raw_response},
            )

        return parse_ocr_response(raw_response, ocr_width, ocr_height)
