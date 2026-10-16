import hashlib
import json
import time
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from core.models import WasteType
from eval.metrics import evaluate_pages
from ingestion.models import ProviderCache
from ingestion.services.llm_client import compute_llm_cache_key
from ingestion.services.normalize import (
    match_nasabah,
    match_waste_type,
    normalize_text,
    parse_date,
    parse_weight,
)
from ingestion.services.preprocess import prepare_image
from ingestion.services.prompts import PROMPT_VERSION, SCHEMA_VERSION
from ingestion.services.score import compute_row_score, route_row
from ingestion.services.strategies import (
    HybridStrategy,
    OcrTextStrategy,
    StrategyOutput,
    VisionStrategy,
)
from ingestion.services.validate import validate_page_rows


class Command(BaseCommand):
    help = "Run evaluation pipeline over the gold dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--gold",
            type=str,
            default="eval/gold",
            help="Path to gold dataset directory.",
        )
        parser.add_argument(
            "--split",
            type=str,
            default="all",
            choices=["dev", "test", "all"],
            help="Dataset split to evaluate.",
        )
        parser.add_argument(
            "--strategy",
            type=str,
            default="ocr_text",
            choices=["vision", "ocr_text", "hybrid"],
            help="Extraction strategy to evaluate.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default="",
            help="Output directory for evaluation results.",
        )
        parser.add_argument(
            "--no-wait",
            action="store_true",
            default=False,
            help="Skip rate-limit pause between uncached Groq calls.",
        )

    def handle(self, *args, **options):
        gold_dir = Path(options["gold"])
        if not gold_dir.exists():
            raise CommandError(f"Gold directory not found: {gold_dir}")

        bank_file = gold_dir / "bank.json"
        if not bank_file.exists():
            raise CommandError(f"Gold bank.json not found: {bank_file}")

        split_filter = options["split"]
        strategy_name = options["strategy"]
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = (
            Path(options["out"])
            if options["out"]
            else Path("eval/results") / f"{ts_str}_{strategy_name}_{split_filter}"
        )
        out_dir.mkdir(parents=True, exist_ok=True)

        if WasteType.objects.count() == 0:
            call_command("loaddata", "core/fixtures/waste_types.json")

        with open(bank_file, encoding="utf-8") as f:
            bank_data = json.load(f)

        nasabah_names: list[str] = bank_data.get("nasabah", [])
        nasabah_uuid_to_name = {
            uuid.uuid5(uuid.NAMESPACE_DNS, f"gold-nasabah:{name}"): name for name in nasabah_names
        }
        nasabah_candidates = [
            (n_uuid, normalize_text(name)) for n_uuid, name in nasabah_uuid_to_name.items()
        ]

        waste_types = WasteType.objects.filter(is_active=True).prefetch_related("aliases")
        wt_uuid_to_code = {wt.id: wt.code for wt in waste_types}
        waste_type_candidates = [
            (wt.id, wt.name_id, [a.alias_normalized for a in wt.aliases.all()])
            for wt in waste_types
        ]

        label_files: list[Path] = []
        for sub in ("synthetic", "real"):
            sub_dir = gold_dir / sub
            if sub_dir.exists():
                label_files.extend(sorted(sub_dir.glob("*.json")))

        selected_labels: list[tuple[Path, dict[str, Any]]] = []
        for lf in label_files:
            with open(lf, encoding="utf-8") as f:
                ldata = json.load(f)
            if split_filter == "all" or ldata.get("split") == split_filter:
                selected_labels.append((lf, ldata))

        if not selected_labels:
            raise CommandError(f"No gold pages found for split='{split_filter}'")

        prev_llm_mode = getattr(settings, "LLM_MODE", "live")
        settings.LLM_MODE = "record"

        pages_results: list[dict[str, Any]] = []
        dummy_bank_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        made_live_groq_call = False

        try:
            for lf_path, ldata in selected_labels:
                page_id = ldata["page_id"]
                img_path = lf_path.parent / ldata["image"]
                if not img_path.exists():
                    raise CommandError(f"Gold image missing: {img_path}")

                raw_bytes = img_path.read_bytes()
                cache_id = hashlib.sha256(raw_bytes).hexdigest()
                prep = prepare_image(raw_bytes)

                llm_strategy_key = "ocr_text" if strategy_name == "ocr_text" else "vision"
                model_name = (
                    getattr(settings, "GROQ_TEXT_MODEL", "qwen/qwen3.8-27b")
                    if llm_strategy_key == "ocr_text"
                    else getattr(settings, "GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
                )
                structured_mode = getattr(settings, "GROQ_STRUCTURED_MODE", "json_schema_strict")
                expected_llm_key = compute_llm_cache_key(
                    cache_image_id=cache_id,
                    prompt_version=PROMPT_VERSION,
                    model=model_name,
                    structured_mode=structured_mode,
                    strategy=llm_strategy_key,
                )
                is_llm_cached = ProviderCache.objects.filter(
                    key=expected_llm_key, kind="llm"
                ).exists()

                if not is_llm_cached and made_live_groq_call and not options["no_wait"]:
                    self.stdout.write("Pausing 25s before next uncached Groq API call...")
                    time.sleep(25)

                self.stdout.write(
                    f"Evaluating page {page_id} ({ldata.get('split')}) "
                    f"with strategy={strategy_name}..."
                )

                output: StrategyOutput
                if strategy_name == "vision":
                    output = VisionStrategy().extract(
                        llm_jpeg=prep.llm_jpeg,
                        cache_image_id=cache_id,
                    )
                elif strategy_name == "ocr_text":
                    output = OcrTextStrategy().extract(
                        ocr_jpeg=prep.ocr_jpeg,
                        ocr_width=prep.ocr_width,
                        ocr_height=prep.ocr_height,
                        cache_image_id=cache_id,
                    )
                else:
                    output = HybridStrategy().extract(
                        llm_jpeg=prep.llm_jpeg,
                        ocr_jpeg=prep.ocr_jpeg,
                        ocr_width=prep.ocr_width,
                        ocr_height=prep.ocr_height,
                        cache_image_id=cache_id,
                    )

                if not is_llm_cached:
                    made_live_groq_call = True

                page_meta = output.raw_extraction.page
                previous_date = None
                row_intermediates = []

                for row_data in output.raw_extraction.rows:
                    weight_kg, weight_flags = parse_weight(
                        row_data.berat_raw,
                        row_data.satuan_raw,
                        default_unit_raw=page_meta.default_unit_raw,
                    )
                    date_val, date_quality, date_flags = parse_date(
                        row_data.tanggal_raw,
                        page_date_raw=page_meta.page_date_raw,
                        upload_year=2026,
                        date_is_repeat=row_data.date_is_repeat,
                        previous_date=previous_date,
                    )
                    if date_val is not None:
                        previous_date = date_val

                    w_code, type_score, type_flags = match_waste_type(
                        row_data.jenis_raw,
                        waste_type_candidates,
                        min_score=getattr(settings, "MATCH_MIN_TYPE", 0.75),
                        ambiguity_margin=getattr(settings, "MATCH_AMBIGUITY_MARGIN", 0.05),
                    )
                    n_name, name_score, name_flags = match_nasabah(
                        row_data.nama_raw,
                        nasabah_candidates,
                        min_score=getattr(settings, "MATCH_MIN_NASABAH", 0.85),
                        ambiguity_margin=getattr(settings, "MATCH_AMBIGUITY_MARGIN", 0.05),
                    )
                    extra_flags = (
                        (output.extra_flags_by_row or {}).get(row_data.row_index, [])
                        if output.extra_flags_by_row
                        else []
                    )
                    initial_flags = (
                        weight_flags + date_flags + type_flags + name_flags + extra_flags
                    )

                    row_intermediates.append(
                        {
                            "row_data": row_data,
                            "weight_kg": weight_kg,
                            "tanggal": date_val,
                            "date_quality": date_quality,
                            "waste_type_id": w_code,
                            "type_score": type_score,
                            "nasabah_id": n_name,
                            "name_score": name_score,
                            "flags": initial_flags,
                            "nama_raw": row_data.nama_raw,
                            "jenis_raw": row_data.jenis_raw,
                            "berat_raw": row_data.berat_raw,
                            "has_correction": row_data.has_correction,
                            "llm_confidence": row_data.row_confidence,
                        }
                    )

                validated_flags_per_row = validate_page_rows(
                    row_intermediates,
                    bank_id=dummy_bank_uuid,
                    today=date(2026, 10, 16),
                )

                t_auto_val = getattr(settings, "T_AUTO", 0.92)
                t_confirm_val = getattr(settings, "T_CONFIRM", 0.60)
                pred_rows_serialized: list[dict[str, Any]] = []

                for idx, inter in enumerate(row_intermediates):
                    final_flags = validated_flags_per_row[idx]
                    score = compute_row_score(
                        llm_confidence=inter["llm_confidence"],
                        type_score=inter["type_score"],
                        name_score=inter["name_score"],
                        weight_kg=inter["weight_kg"],
                        date_val=inter["tanggal"],
                        date_quality=inter["date_quality"],
                        flags=final_flags,
                    )
                    route = route_row(
                        score=score,
                        flags=final_flags,
                        auto_save_enabled=True,
                        t_auto=t_auto_val,
                        t_confirm=t_confirm_val,
                    )
                    r_raw = inter["row_data"]
                    pred_rows_serialized.append(
                        {
                            "row_index": r_raw.row_index,
                            "tanggal_raw": r_raw.tanggal_raw,
                            "nama_raw": r_raw.nama_raw,
                            "jenis_raw": r_raw.jenis_raw,
                            "berat_raw": r_raw.berat_raw,
                            "tanggal": str(inter["tanggal"]) if inter["tanggal"] else None,
                            "nasabah": nasabah_uuid_to_name.get(inter["nasabah_id"]),
                            "waste_type_code": wt_uuid_to_code.get(inter["waste_type_id"]),
                            "weight_kg": (
                                f"{inter['weight_kg']:.3f}"
                                if inter["weight_kg"] is not None
                                else None
                            ),
                            "score": score,
                            "route": route,
                            "flags": final_flags,
                        }
                    )

                pages_results.append(
                    {
                        "page_id": page_id,
                        "split": ldata.get("split", "dev"),
                        "provenance": ldata.get("provenance", "synthetic"),
                        "strategy": strategy_name,
                        "latency_ms": output.extraction_result.latency_ms,
                        "prompt_tokens": output.extraction_result.prompt_tokens,
                        "completion_tokens": output.extraction_result.completion_tokens,
                        "gold_rows": ldata.get("rows", []),
                        "pred_rows": pred_rows_serialized,
                    }
                )
        finally:
            settings.LLM_MODE = prev_llm_mode

        t_auto_default = getattr(settings, "T_AUTO", 0.92)
        t_confirm_default = getattr(settings, "T_CONFIRM", 0.60)
        overall_metrics = evaluate_pages(
            pages_results,
            t_auto=t_auto_default,
            t_confirm=t_confirm_default,
        )

        payload = {
            "timestamp": ts_str,
            "strategy": strategy_name,
            "split": split_filter,
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "model": (
                getattr(settings, "GROQ_TEXT_MODEL", "qwen/qwen3.8-27b")
                if strategy_name == "ocr_text"
                else getattr(settings, "GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
            ),
            "metrics": overall_metrics,
            "pages": pages_results,
        }

        out_file = out_dir / "run_results.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        exact_pct = overall_metrics["row_exact_rate"] * 100
        self.stdout.write(
            self.style.SUCCESS(
                f"Evaluation complete: strategy={strategy_name}, split={split_filter}, "
                f"n={overall_metrics['n_gold']}, exact={exact_pct:.1f}%, "
                f"auto_prec={overall_metrics['auto_precision'] * 100:.1f}%, "
                f"auto_cov={overall_metrics['auto_coverage'] * 100:.1f}%, "
                f"unsafe_auto={overall_metrics['unsafe_auto_rate'] * 100:.1f}%, "
                f"p50={overall_metrics['latency_p50_s']:.2f}s -> {out_file}"
            )
        )
