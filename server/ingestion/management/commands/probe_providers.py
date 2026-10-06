import base64
import os
import time
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from groq import Groq

from ingestion.services.preprocess import prepare_image
from ingestion.services.prompts import VISION_SYSTEM_PROMPT
from ingestion.services.schemas import RawExtraction, clean_json_text, get_strict_json_schema


class Command(BaseCommand):
    help = "Probe Groq and OCR.space provider endpoints and output compatibility report."

    def add_arguments(self, parser):
        parser.add_argument(
            "--image",
            type=str,
            required=True,
            help="Path to ledger image file to probe providers with.",
        )

    def handle(self, *args, **options):
        image_path = Path(options["image"])
        if not image_path.exists():
            raise CommandError(f"Image file not found: {image_path}")

        with open(image_path, "rb") as f:
            raw_bytes = f.read()

        self.stdout.write(self.style.NOTICE("=== EcoTrack Provider Probe ==="))
        self.stdout.write(f"Preprocessing input image: {image_path.name}")
        prepared = prepare_image(raw_bytes)
        self.stdout.write(
            f"Prepared: LLM JPEG {prepared.width}x{prepared.height} "
            f"({len(prepared.llm_jpeg)} bytes), "
            f"OCR JPEG {prepared.ocr_width}x{prepared.ocr_height} "
            f"({len(prepared.ocr_jpeg)} bytes)\n"
        )

        groq_api_key = getattr(settings, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
        ocr_api_key = getattr(settings, "OCR_SPACE_API_KEY", "") or os.environ.get(
            "OCR_SPACE_API_KEY", ""
        )

        self._probe_groq(
            api_key=groq_api_key,
            jpeg_bytes=prepared.llm_jpeg,
            structured_mode="json_schema_strict",
        )
        self._probe_groq(
            api_key=groq_api_key,
            jpeg_bytes=prepared.llm_jpeg,
            structured_mode="json_object",
        )
        self._probe_ocr(
            api_key=ocr_api_key,
            jpeg_bytes=prepared.ocr_jpeg,
            engine=2,
            ocr_width=prepared.ocr_width,
            ocr_height=prepared.ocr_height,
        )
        self._probe_ocr(
            api_key=ocr_api_key,
            jpeg_bytes=prepared.ocr_jpeg,
            engine=3,
            ocr_width=prepared.ocr_width,
            ocr_height=prepared.ocr_height,
        )

    def _probe_groq(self, api_key: str, jpeg_bytes: bytes, structured_mode: str):
        label = f"Groq Vision ({structured_mode})"
        self.stdout.write(f"--- Testing {label} ---")
        if not api_key:
            self.stdout.write(self.style.WARNING("SKIPPED: GROQ_API_KEY is not configured\n"))
            return

        model = getattr(settings, "GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
        client = Groq(api_key=api_key, max_retries=0, timeout=60)
        b64_image = base64.b64encode(jpeg_bytes).decode("ascii")
        image_url = f"data:image/jpeg;base64,{b64_image}"

        messages = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    }
                ],
            },
        ]

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "max_completion_tokens": 3000,
        }

        if structured_mode == "json_schema_strict":
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "raw_extraction",
                    "strict": True,
                    "schema": get_strict_json_schema(),
                },
            }
        else:
            kwargs["response_format"] = {"type": "json_object"}

        reasoning_effort = getattr(settings, "GROQ_REASONING_EFFORT", None)
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort

        start_time = time.monotonic()
        try:
            completion = client.chat.completions.create(**kwargs)
            latency_ms = int((time.monotonic() - start_time) * 1000)
            content = completion.choices[0].message.content or ""
            cleaned = clean_json_text(content)
            parsed = RawExtraction.model_validate_json(cleaned)

            self.stdout.write(self.style.SUCCESS(f"STATUS: PASS (Latency: {latency_ms} ms)"))
            usage = completion.usage
            if usage:
                self.stdout.write(
                    f"Usage: prompt_tokens={usage.prompt_tokens}, "
                    f"completion_tokens={usage.completion_tokens}, "
                    f"total={usage.total_tokens}"
                )
            self.stdout.write(f"Extracted Rows: {len(parsed.rows)}\n")
        except Exception as exc:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            self.stdout.write(self.style.ERROR(f"STATUS: FAIL (Latency: {latency_ms} ms)"))
            self.stdout.write(f"Error text: {exc}\n")

    def _probe_ocr(
        self, api_key: str, jpeg_bytes: bytes, engine: int, ocr_width: int, ocr_height: int
    ):
        label = f"OCR.space Engine {engine}"
        self.stdout.write(f"--- Testing {label} ---")
        if not api_key:
            self.stdout.write(self.style.WARNING("SKIPPED: OCR_SPACE_API_KEY is not configured\n"))
            return

        url = "https://api.ocr.space/parse/image"
        data = {
            "apikey": api_key,
            "OCREngine": str(engine),
            "isOverlayRequired": "true",
            "isTable": "true",
            "detectOrientation": "true",
            "scale": "true",
            "language": "eng",
        }
        files = {
            "file": ("probe_ocr.jpg", jpeg_bytes, "image/jpeg"),
        }

        start_time = time.monotonic()
        try:
            resp = requests.post(url, data=data, files=files, timeout=45)
            latency_ms = int((time.monotonic() - start_time) * 1000)

            if resp.status_code != 200:
                self.stdout.write(self.style.ERROR(f"STATUS: FAIL HTTP {resp.status_code}"))
                self.stdout.write(f"Response: {resp.text}\n")
                return

            parsed_json = resp.json()
            is_errored = parsed_json.get("IsErroredOnProcessing")
            if is_errored:
                err_msg = parsed_json.get("ErrorMessage")
                self.stdout.write(self.style.ERROR("STATUS: FAIL (Processing Error)"))
                self.stdout.write(f"Error text: {err_msg}")
                self.stdout.write(f"Error details: {parsed_json.get('ErrorDetails')}\n")
                return

            parsed_results = parsed_json.get("ParsedResults") or []
            lines_count = 0
            if parsed_results:
                overlay = parsed_results[0].get("TextOverlay") or {}
                lines_count = len(overlay.get("Lines") or [])

            self.stdout.write(self.style.SUCCESS(f"STATUS: PASS (Latency: {latency_ms} ms)"))
            proc_ms = parsed_json.get("ProcessingTimeInMilliseconds")
            self.stdout.write(f"Processing time (OCR.space reported): {proc_ms} ms")
            self.stdout.write(f"Overlay Lines recognized: {lines_count}\n")
        except Exception as exc:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            self.stdout.write(self.style.ERROR(f"STATUS: FAIL (Latency: {latency_ms} ms)"))
            self.stdout.write(f"Error text: {exc}\n")
