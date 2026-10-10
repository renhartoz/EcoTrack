import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from groq import Groq, RateLimitError

from ingestion.services.llm_client import inject_json_object_prompt
from ingestion.services.ocr_client import parse_ocr_response
from ingestion.services.preprocess import prepare_image
from ingestion.services.prompts import VISION_SYSTEM_PROMPT
from ingestion.services.schemas import (
    RawExtraction,
    RawRow,
    VisionExtraction,
    clean_json_text,
    get_strict_json_schema,
    vision_row_to_raw,
)


class Command(BaseCommand):
    help = "Probe Groq and OCR.space provider endpoints and output compatibility report."

    def add_arguments(self, parser):
        parser.add_argument(
            "--image",
            type=str,
            required=True,
            help="Path to ledger image file to probe providers with.",
        )
        parser.add_argument(
            "--save-dir",
            type=str,
            default="eval/results/probe/",
            help="Directory to save probe results as JSON (default: eval/results/probe/).",
        )
        parser.add_argument(
            "--no-wait",
            action="store_true",
            default=False,
            help="Skip 65s wait between Groq calls.",
        )

    def handle(self, *args, **options):
        image_path = Path(options["image"])
        if not image_path.exists():
            raise CommandError(f"Image file not found: {image_path}")

        save_dir = Path(options["save_dir"])
        save_dir.mkdir(parents=True, exist_ok=True)

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
            save_dir=save_dir,
        )

        if not options["no_wait"] and groq_api_key:
            self.stdout.write(
                "Waiting 65 seconds before next Groq call to respect rate limits...\n"
            )
            time.sleep(65)

        self._probe_groq(
            api_key=groq_api_key,
            jpeg_bytes=prepared.llm_jpeg,
            structured_mode="json_object",
            save_dir=save_dir,
        )
        self._probe_ocr(
            api_key=ocr_api_key,
            jpeg_bytes=prepared.ocr_jpeg,
            engine=2,
            ocr_width=prepared.ocr_width,
            ocr_height=prepared.ocr_height,
            save_dir=save_dir,
        )
        self._probe_ocr(
            api_key=ocr_api_key,
            jpeg_bytes=prepared.ocr_jpeg,
            engine=3,
            ocr_width=prepared.ocr_width,
            ocr_height=prepared.ocr_height,
            save_dir=save_dir,
        )

    def _print_rows_table(self, rows: list[RawRow]):
        headers = [
            "index",
            "tanggal_raw",
            "nama_raw",
            "jenis_raw",
            "berat_raw",
            "satuan_raw",
            "row_confidence",
            "y_min",
            "y_max",
        ]
        data = []
        for r in rows:
            conf_str = f"{r.row_confidence:.2f}"
            ymin_str = f"{r.y_min:.3f}" if r.y_min is not None else "-"
            ymax_str = f"{r.y_max:.3f}" if r.y_max is not None else "-"
            data.append(
                [
                    str(r.row_index),
                    str(r.tanggal_raw if r.tanggal_raw is not None else "-"),
                    str(r.nama_raw if r.nama_raw is not None else "-"),
                    str(r.jenis_raw if r.jenis_raw is not None else "-"),
                    str(r.berat_raw if r.berat_raw is not None else "-"),
                    str(r.satuan_raw if r.satuan_raw is not None else "-"),
                    conf_str,
                    ymin_str,
                    ymax_str,
                ]
            )

        col_widths = [len(h) for h in headers]
        for row in data:
            for idx, val in enumerate(row):
                col_widths[idx] = max(col_widths[idx], len(val))

        header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        separator_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
        self.stdout.write(header_line)
        self.stdout.write(separator_line)
        for row in data:
            self.stdout.write(" | ".join(val.ljust(col_widths[i]) for i, val in enumerate(row)))
        self.stdout.write("")

    def _probe_groq(
        self,
        api_key: str,
        jpeg_bytes: bytes,
        structured_mode: str,
        save_dir: Path,
    ):
        label = f"Groq Vision ({structured_mode})"
        self.stdout.write(f"--- Testing {label} ---")
        if not api_key:
            self.stdout.write(self.style.WARNING("SKIPPED: GROQ_API_KEY is not configured\n"))
            return

        model = getattr(settings, "GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
        max_completion_tokens = getattr(settings, "GROQ_MAX_COMPLETION_TOKENS", 3000)
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

        if structured_mode == "json_schema_strict":
            response_format_type = "json_schema"
            call_messages = messages
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "raw_extraction",
                    "strict": True,
                    "schema": get_strict_json_schema(VisionExtraction),
                },
            }
        else:
            response_format_type = "json_object"
            call_messages = inject_json_object_prompt(messages, VisionExtraction, "vision")
            response_format = {"type": "json_object"}

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": call_messages,
            "temperature": 0.0,
            "max_completion_tokens": max_completion_tokens,
            "response_format": response_format,
        }

        reasoning_effort = getattr(settings, "GROQ_REASONING_EFFORT", None)
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort

        start_time = time.monotonic()
        rate_limit_headers: dict[str, str] = {}

        try:
            raw_res = client.chat.completions.with_raw_response.create(**kwargs)
            completion = raw_res.parse()
            latency_ms = int((time.monotonic() - start_time) * 1000)

            for k, v in raw_res.headers.items():
                if "ratelimit" in k.lower() or k.lower() == "retry-after":
                    rate_limit_headers[k] = v

            content = completion.choices[0].message.content or ""
            cleaned = clean_json_text(content)
            try:
                parsed_vision = VisionExtraction.model_validate_json(cleaned)
                parsed_page = parsed_vision.page
                parsed_rows = [
                    vision_row_to_raw(r, idx + 1) for idx, r in enumerate(parsed_vision.rows)
                ]
            except Exception:
                parsed_raw = RawExtraction.model_validate_json(cleaned)
                parsed_page = parsed_raw.page
                parsed_rows = parsed_raw.rows

            self.stdout.write(self.style.SUCCESS(f"STATUS: PASS (Latency: {latency_ms} ms)"))
            usage = completion.usage
            usage_dict = {}
            if usage:
                usage_dict = {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                }
                self.stdout.write(
                    f"Usage: prompt_tokens={usage.prompt_tokens}, "
                    f"completion_tokens={usage.completion_tokens}, "
                    f"total={usage.total_tokens}"
                )
                self.stdout.write(f"Output token count: {usage.completion_tokens}")
            if rate_limit_headers:
                self.stdout.write("Rate limit headers:")
                for k, v in rate_limit_headers.items():
                    self.stdout.write(f"  {k}: {v}")

            self.stdout.write(f"Extracted Rows: {len(parsed_rows)}\n")
            self._print_rows_table(parsed_rows)

            save_payload = {
                "request_parameters": {
                    "model": model,
                    "max_completion_tokens": max_completion_tokens,
                    "response_format_type": response_format_type,
                    "reasoning_setting": reasoning_effort,
                },
                "rate_limit_headers": rate_limit_headers,
                "page": parsed_page.model_dump(),
                "rows": [r.model_dump() for r in parsed_rows],
                "usage": usage_dict,
            }
            out_file = save_dir / f"groq_{structured_mode}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(save_payload, f, indent=2)
            self.stdout.write(f"Saved extraction result to: {out_file}\n")

        except RateLimitError as exc:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            self.stdout.write(
                self.style.ERROR(f"STATUS: FAIL (429 Rate Limited - {latency_ms} ms)")
            )
            self.stdout.write(f"max_completion_tokens sent: {max_completion_tokens}")
            self.stdout.write(f"Full error text: {exc}\n")

            if hasattr(exc, "response") and hasattr(exc.response, "headers"):
                for k, v in exc.response.headers.items():
                    if "ratelimit" in k.lower() or k.lower() == "retry-after":
                        rate_limit_headers[k] = v

            err_payload = {
                "request_parameters": {
                    "model": model,
                    "max_completion_tokens": max_completion_tokens,
                    "response_format_type": response_format_type,
                    "reasoning_setting": reasoning_effort,
                },
                "rate_limit_headers": rate_limit_headers,
                "error": str(exc),
            }
            out_file = save_dir / f"groq_{structured_mode}_error.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(err_payload, f, indent=2)

        except Exception as exc:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            is_429 = "429" in str(exc)
            if is_429:
                self.stdout.write(
                    self.style.ERROR(f"STATUS: FAIL (429 Rate Limited - {latency_ms} ms)")
                )
                self.stdout.write(f"max_completion_tokens sent: {max_completion_tokens}")
            else:
                self.stdout.write(self.style.ERROR(f"STATUS: FAIL (Latency: {latency_ms} ms)"))
            self.stdout.write(f"Error text: {exc}\n")

    def _probe_ocr(
        self,
        api_key: str,
        jpeg_bytes: bytes,
        engine: int,
        ocr_width: int,
        ocr_height: int,
        save_dir: Path,
    ):
        label = f"OCR.space Engine {engine}"
        self.stdout.write(f"--- Testing {label} ---")
        if not api_key:
            self.stdout.write(self.style.WARNING("SKIPPED: OCR_SPACE_API_KEY is not configured\n"))
            return

        url = "https://api.ocr.space/parse/image"
        request_params = {
            "OCREngine": str(engine),
            "isOverlayRequired": "true",
            "isTable": "true",
            "detectOrientation": "true",
            "scale": "true",
            "language": "eng",
        }
        data = dict(request_params)
        data["apikey"] = api_key
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

            ocr_result = parse_ocr_response(parsed_json, ocr_width, ocr_height)

            self.stdout.write(self.style.SUCCESS(f"STATUS: PASS (Latency: {latency_ms} ms)"))
            proc_ms = parsed_json.get("ProcessingTimeInMilliseconds")
            self.stdout.write(f"Processing time (OCR.space reported): {proc_ms} ms")
            self.stdout.write(f"Overlay Lines recognized: {len(ocr_result.lines)}\n")

            self.stdout.write(f"First 25 OCR Lines (Engine {engine}):")
            display_lines = ocr_result.lines[:25]
            if not display_lines:
                self.stdout.write("  (no lines recognized)")
            else:
                for line in display_lines:
                    self.stdout.write(
                        f"  [{line.line_number:02d}] (y_min={line.y_min:.3f}) {line.text}"
                    )
            self.stdout.write("")

            serialized_lines = [
                {
                    "line_number": line.line_number,
                    "text": line.text,
                    "y_min": line.y_min,
                    "y_max": line.y_max,
                    "x_min": line.x_min,
                    "x_max": line.x_max,
                    "words": [
                        {
                            "text": w.text,
                            "y_min": w.y_min,
                            "y_max": w.y_max,
                            "x_min": w.x_min,
                            "x_max": w.x_max,
                        }
                        for w in line.words
                    ],
                }
                for line in ocr_result.lines
            ]

            save_payload = {
                "request_parameters": request_params,
                "lines": serialized_lines,
            }
            out_file = save_dir / f"ocr_engine_{engine}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(save_payload, f, indent=2)
            self.stdout.write(f"Saved OCR result to: {out_file}\n")

        except Exception as exc:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            self.stdout.write(self.style.ERROR(f"STATUS: FAIL (Latency: {latency_ms} ms)"))
            self.stdout.write(f"Error text: {exc}\n")
