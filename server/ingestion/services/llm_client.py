import base64
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from groq import APIError, APITimeoutError, Groq, RateLimitError
from pydantic import BaseModel, ValidationError

from ingestion.models import ProviderCache
from ingestion.services.ocr_client import ReplayMissError
from ingestion.services.prompts import (
    PROMPT_VERSION,
    SCHEMA_REPAIR_PROMPT,
    VISION_SYSTEM_PROMPT,
)
from ingestion.services.schemas import (
    OcrTextExtraction,
    PageMeta,
    RawExtraction,
    RawRow,
    TextExtraction,
    VisionExtraction,
    clean_json_text,
    get_strict_json_schema,
    ocr_text_row_to_raw,
    text_row_to_raw,
    vision_row_to_raw,
)


class LlmError(Exception):
    pass


class LlmTimeoutError(LlmError):
    pass


class LlmRateLimitedError(LlmError):
    pass


class LlmSchemaInvalidError(LlmError):
    pass


class LlmApiError(LlmError):
    pass


@dataclass(frozen=True)
class ExtractionResult:
    raw_extraction: RawExtraction
    raw_response: dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


def compute_llm_cache_key(
    cache_image_id: str,
    prompt_version: str,
    model: str,
    structured_mode: str,
    strategy: str,
) -> str:
    raw_key = f"llm:{cache_image_id}:{prompt_version}:{model}:{structured_mode}:{strategy}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_strategy_wire_model(strategy: str) -> type[BaseModel]:
    if strategy == "ocr_text":
        return OcrTextExtraction
    if strategy == "text":
        return TextExtraction
    return VisionExtraction


def get_strategy_example(strategy: str) -> dict[str, Any]:
    if strategy == "ocr_text":
        return {
            "page": {
                "bank_name_raw": None,
                "page_date_raw": "Oktober 2026",
                "default_unit_raw": "kg",
                "has_total_row": False,
                "total_raw": None,
            },
            "rows": [
                {
                    "tanggal_raw": "01/10",
                    "date_is_repeat": False,
                    "nama_raw": "Bu Siti",
                    "jenis_raw": "Kardus",
                    "berat_raw": "4,5 kg",
                    "row_confidence": 0.95,
                    "source_lines": [2, 3],
                }
            ],
        }
    if strategy == "text":
        return {
            "page": {
                "bank_name_raw": None,
                "page_date_raw": "Oktober 2026",
                "default_unit_raw": None,
                "has_total_row": False,
                "total_raw": None,
            },
            "rows": [
                {
                    "tanggal_raw": "01/10",
                    "date_is_repeat": False,
                    "nama_raw": "Bu Siti",
                    "jenis_raw": "Kardus",
                    "berat_raw": "4,5 kg",
                    "row_confidence": 0.95,
                    "evidence_text": "01/10 Bu Siti kardus 4,5 kg",
                }
            ],
        }
    return {
        "page": {
            "bank_name_raw": None,
            "page_date_raw": "Oktober 2026",
            "default_unit_raw": "kg",
            "has_total_row": False,
            "total_raw": None,
        },
        "rows": [
            {
                "tanggal_raw": "01/10",
                "date_is_repeat": False,
                "nama_raw": "Bu Siti",
                "jenis_raw": "Kardus",
                "berat_raw": "4,5 kg",
                "has_correction": False,
                "row_confidence": 0.95,
            }
        ],
    }


def inject_json_object_prompt(
    messages: list[dict[str, Any]],
    model_cls: type[BaseModel],
    strategy: str,
) -> list[dict[str, Any]]:
    schema_dict = get_strict_json_schema(model_cls)
    example_dict = get_strategy_example(strategy)
    schema_str = json.dumps(schema_dict, indent=2)
    example_str = json.dumps(example_dict, indent=2)

    prompt_suffix = (
        f"\n\nJSON Schema:\n{schema_str}\n\n"
        f"Example JSON:\n{example_str}\n\n"
        "Output exactly one valid JSON object adhering strictly to the above schema."
    )

    new_messages: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") == "system":
            new_messages.append(
                {"role": "system", "content": f"{msg.get('content', '')}{prompt_suffix}"}
            )
        else:
            new_messages.append(dict(msg))
    return new_messages


class GroqExtractor:
    def __init__(
        self,
        api_key: str | None = None,
        vision_model: str | None = None,
        text_model: str | None = None,
        structured_mode: str | None = None,
        timeout: int | None = None,
        max_completion_tokens: int | None = None,
        max_retry_wait_s: int | None = None,
        reasoning_effort: str | None = None,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "GROQ_API_KEY", "")
        self.vision_model = vision_model or getattr(
            settings, "GROQ_VISION_MODEL", "qwen/qwen3.8-27b"
        )
        self.text_model = text_model or getattr(settings, "GROQ_TEXT_MODEL", "qwen/qwen3.8-27b")
        self.structured_mode = structured_mode or getattr(
            settings, "GROQ_STRUCTURED_MODE", "json_schema_strict"
        )
        self.timeout = timeout if timeout is not None else getattr(settings, "LLM_TIMEOUT_S", 60)
        self.max_completion_tokens = (
            max_completion_tokens
            if max_completion_tokens is not None
            else getattr(settings, "GROQ_MAX_COMPLETION_TOKENS", 3000)
        )
        self.max_retry_wait_s = (
            max_retry_wait_s
            if max_retry_wait_s is not None
            else getattr(settings, "GROQ_MAX_RETRY_WAIT_S", 20)
        )
        self.reasoning_effort = (
            reasoning_effort
            if reasoning_effort is not None
            else getattr(settings, "GROQ_REASONING_EFFORT", None)
        )

    def extract_from_image(
        self,
        jpeg_bytes: bytes,
        cache_image_id: str | None = None,
        system_prompt: str = VISION_SYSTEM_PROMPT,
        strategy: str = "vision",
    ) -> ExtractionResult:
        cache_id = cache_image_id or hashlib.sha256(jpeg_bytes).hexdigest()
        b64_image = base64.b64encode(jpeg_bytes).decode("ascii")
        image_url = f"data:image/jpeg;base64,{b64_image}"

        messages = [
            {"role": "system", "content": system_prompt},
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
        return self._execute_extraction(
            messages=messages,
            model=self.vision_model,
            cache_image_id=cache_id,
            strategy=strategy,
        )

    def extract_from_text(
        self,
        text: str,
        cache_image_id: str | None = None,
        system_prompt: str = VISION_SYSTEM_PROMPT,
        strategy: str = "text",
    ) -> ExtractionResult:
        cache_id = cache_image_id or hashlib.sha256(text.encode("utf-8")).hexdigest()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        return self._execute_extraction(
            messages=messages,
            model=self.text_model,
            cache_image_id=cache_id,
            strategy=strategy,
        )

    def _execute_extraction(
        self,
        messages: list[dict[str, Any]],
        model: str,
        cache_image_id: str,
        strategy: str,
    ) -> ExtractionResult:
        mode = getattr(settings, "LLM_MODE", "live")
        cache_key = compute_llm_cache_key(
            cache_image_id=cache_image_id,
            prompt_version=PROMPT_VERSION,
            model=model,
            structured_mode=self.structured_mode,
            strategy=strategy,
        )

        if mode == "fake":
            return self._handle_fake_execution(strategy)

        if mode == "replay":
            cached = ProviderCache.objects.filter(key=cache_key, kind="llm").first()
            if not cached:
                raise ReplayMissError("Replay miss for LLM cache key")
            return self._parse_completion_response(cached.response, 0, strategy=strategy)

        model_cls = get_strategy_wire_model(strategy)
        call_messages = (
            inject_json_object_prompt(messages, model_cls, strategy)
            if self.structured_mode == "json_object"
            else messages
        )

        start_time = time.monotonic()
        raw_response = self._call_groq_with_retries(
            messages=call_messages, model=model, model_cls=model_cls
        )
        latency_ms = int((time.monotonic() - start_time) * 1000)

        try:
            result = self._parse_completion_response(raw_response, latency_ms, strategy=strategy)
        except ValidationError:
            raw_response = self._retry_schema_repair(
                messages=call_messages,
                model=model,
                failed_response=raw_response,
                model_cls=model_cls,
            )
            latency_ms = int((time.monotonic() - start_time) * 1000)
            try:
                result = self._parse_completion_response(
                    raw_response, latency_ms, strategy=strategy
                )
            except ValidationError as exc:
                raise LlmSchemaInvalidError(
                    "Output failed schema validation after repair attempt"
                ) from exc

        if mode == "record":
            ProviderCache.objects.update_or_create(
                key=cache_key,
                defaults={"kind": "llm", "response": raw_response},
            )

        return result

    def _call_groq_with_retries(
        self,
        messages: list[dict[str, Any]],
        model: str,
        model_cls: type[BaseModel] = VisionExtraction,
    ) -> dict[str, Any]:
        client = Groq(api_key=self.api_key, max_retries=0, timeout=self.timeout)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "max_completion_tokens": self.max_completion_tokens,
        }

        if self.structured_mode == "json_schema_strict":
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "raw_extraction",
                    "strict": True,
                    "schema": get_strict_json_schema(model_cls),
                },
            }
        else:
            kwargs["response_format"] = {"type": "json_object"}

        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort

        try:
            completion = client.chat.completions.create(**kwargs)
            return completion.model_dump()
        except RateLimitError as exc:
            retry_after = self._parse_retry_after(exc)
            if retry_after is not None and retry_after > self.max_retry_wait_s:
                raise LlmRateLimitedError("Groq rate limit retry-after exceeds wait limit") from exc
            wait_s = retry_after if retry_after is not None else 1.0
            time.sleep(wait_s)
            try:
                completion = client.chat.completions.create(**kwargs)
                return completion.model_dump()
            except RateLimitError as retry_exc:
                raise LlmRateLimitedError("Groq rate limit hit on retry") from retry_exc
            except Exception as retry_exc:
                raise LlmApiError("Groq call failed on rate limit retry") from retry_exc
        except APITimeoutError as exc:
            raise LlmTimeoutError("Groq request timed out") from exc
        except APIError as exc:
            raise LlmApiError(f"Groq API error: {exc}") from exc
        except Exception as exc:
            raise LlmApiError(f"Unexpected Groq client failure: {exc}") from exc

    def _retry_schema_repair(
        self,
        messages: list[dict[str, Any]],
        model: str,
        failed_response: dict[str, Any],
        model_cls: type[BaseModel] = VisionExtraction,
    ) -> dict[str, Any]:
        choices = failed_response.get("choices") or []
        first_choice = choices[0] if choices else {}
        msg_obj = first_choice.get("message") or {}
        content = msg_obj.get("content") or ""

        repair_messages = list(messages) + [
            {"role": "assistant", "content": content},
            {"role": "user", "content": SCHEMA_REPAIR_PROMPT},
        ]
        return self._call_groq_with_retries(
            messages=repair_messages, model=model, model_cls=model_cls
        )

    def _parse_retry_after(self, exc: RateLimitError) -> float | None:
        response = getattr(exc, "response", None)
        if response is not None:
            headers = getattr(response, "headers", {})
            val = headers.get("retry-after")
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
        return None

    def _dict_to_raw_extraction(
        self,
        data: dict[str, Any],
        model_cls: type[BaseModel],
    ) -> RawExtraction:
        page_dict = data.get("page")
        rows_list = data.get("rows")
        if not isinstance(page_dict, dict) or not isinstance(rows_list, list):
            raise LlmSchemaInvalidError("Response missing valid page or rows object")

        try:
            wire = model_cls.model_validate({"page": page_dict, "rows": rows_list})
            return self._wire_to_raw_extraction(wire)
        except ValidationError:
            page_meta = PageMeta(
                bank_name_raw=page_dict.get("bank_name_raw"),
                page_date_raw=page_dict.get("page_date_raw"),
                default_unit_raw=page_dict.get("default_unit_raw"),
                has_total_row=bool(page_dict.get("has_total_row", False)),
                total_raw=page_dict.get("total_raw"),
            )
            is_ocr_strategy = model_cls == OcrTextExtraction
            raw_rows = [
                RawRow(
                    row_index=int(r.get("row_index", idx)),
                    tanggal_raw=r.get("tanggal_raw"),
                    date_is_repeat=bool(r.get("date_is_repeat", False)),
                    nama_raw=r.get("nama_raw"),
                    jenis_raw=r.get("jenis_raw"),
                    berat_raw=r.get("berat_raw"),
                    satuan_raw=r.get("satuan_raw"),
                    evidence_text=str(r.get("evidence_text", "")),
                    has_correction=bool(r.get("has_correction", False)),
                    row_confidence=float(r.get("row_confidence", 0.0)),
                    y_min=(
                        float(r["y_min"])
                        if r.get("y_min") is not None and is_ocr_strategy
                        else None
                    ),
                    y_max=(
                        float(r["y_max"])
                        if r.get("y_max") is not None and is_ocr_strategy
                        else None
                    ),
                    source_lines=r.get("source_lines"),
                )
                for idx, r in enumerate(rows_list)
            ]
            return RawExtraction(page=page_meta, rows=raw_rows)

    def _wire_to_raw_extraction(
        self,
        wire: BaseModel,
    ) -> RawExtraction:
        if isinstance(wire, VisionExtraction):
            return RawExtraction(
                page=wire.page,
                rows=[vision_row_to_raw(r, idx) for idx, r in enumerate(wire.rows)],
            )
        if isinstance(wire, OcrTextExtraction):
            return RawExtraction(
                page=wire.page,
                rows=[ocr_text_row_to_raw(r, idx) for idx, r in enumerate(wire.rows)],
            )
        if isinstance(wire, TextExtraction):
            return RawExtraction(
                page=wire.page,
                rows=[text_row_to_raw(r, idx) for idx, r in enumerate(wire.rows)],
            )
        if isinstance(wire, RawExtraction):
            return wire
        raise ValueError(f"Unknown wire extraction type: {type(wire)}")

    def _parse_completion_response(
        self,
        raw_response: dict[str, Any],
        latency_ms: int,
        strategy: str = "vision",
    ) -> ExtractionResult:
        choices = raw_response.get("choices") or []
        model_cls = get_strategy_wire_model(strategy)

        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content") or ""
            cleaned = clean_json_text(content)
            try:
                wire = model_cls.model_validate_json(cleaned)
                raw_extraction = self._wire_to_raw_extraction(wire)
            except ValidationError:
                raw_extraction = RawExtraction.model_validate_json(cleaned)
        elif "rows" in raw_response and "page" in raw_response:
            raw_extraction = self._dict_to_raw_extraction(raw_response, model_cls)
        else:
            raise LlmSchemaInvalidError("Response choices array is empty")

        usage = raw_response.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)

        return ExtractionResult(
            raw_extraction=raw_extraction,
            raw_response=raw_response,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )

    def _handle_fake_execution(self, strategy: str = "vision") -> ExtractionResult:
        fixture_path = (
            Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "groq_vision_valid.json"
        )
        with open(fixture_path, encoding="utf-8") as f:
            raw_response = json.load(f)
        return self._parse_completion_response(raw_response, 100, strategy=strategy)
