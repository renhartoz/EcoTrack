from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from deposits.models import Deposit


def deduplicate_flags(flags: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    deduped = []
    for f in flags:
        code = f["code"]
        if code not in seen:
            seen.add(code)
            deduped.append(f)
    return deduped


def validate_row_single(
    nama_raw: str | None,
    jenis_raw: str | None,
    berat_raw: str | None,
    has_correction: bool,
    llm_confidence: float,
    tanggal: date | None,
    nasabah_id: int | None,
    waste_type_id: int | None,
    weight_kg: Decimal | None,
    initial_flags: list[dict[str, str]],
    today: date,
    max_weight: float | None = None,
) -> list[dict[str, str]]:
    flags = list(initial_flags)

    if not nama_raw or not nama_raw.strip():
        flags.append({"code": "ILLEGIBLE_FIELD", "severity": "hard"})
    if not jenis_raw or not jenis_raw.strip():
        flags.append({"code": "ILLEGIBLE_FIELD", "severity": "hard"})
    if not berat_raw or not berat_raw.strip():
        flags.append({"code": "ILLEGIBLE_FIELD", "severity": "hard"})

    if max_weight is None:
        max_weight = getattr(settings, "MAX_WEIGHT_KG_PER_ROW", 200.0)

    if weight_kg is not None and weight_kg > Decimal(str(max_weight)):
        flags.append({"code": "WEIGHT_OUT_OF_RANGE", "severity": "soft"})

    min_date = today - timedelta(days=400)
    max_date = today + timedelta(days=1)
    if tanggal is not None:
        if tanggal < min_date or tanggal > max_date:
            flags.append({"code": "DATE_OUT_OF_RANGE", "severity": "soft"})

    if llm_confidence < 0.5:
        flags.append({"code": "LOW_LLM_CONFIDENCE", "severity": "soft"})

    if has_correction:
        flags.append({"code": "CORRECTION_PRESENT", "severity": "soft"})

    return deduplicate_flags(flags)


def validate_page_rows(
    rows_data: list[dict],
    bank_id: int,
    today: date | None = None,
) -> list[list[dict[str, str]]]:
    if today is None:
        today = date.today()

    max_weight = getattr(settings, "MAX_WEIGHT_KG_PER_ROW", 200.0)
    per_row_flags = []

    for r in rows_data:
        flags = validate_row_single(
            nama_raw=r.get("nama_raw"),
            jenis_raw=r.get("jenis_raw"),
            berat_raw=r.get("berat_raw"),
            has_correction=r.get("has_correction", False),
            llm_confidence=r.get("llm_confidence", 1.0),
            tanggal=r.get("tanggal"),
            nasabah_id=r.get("nasabah_id"),
            waste_type_id=r.get("waste_type_id"),
            weight_kg=r.get("weight_kg"),
            initial_flags=r.get("flags", []),
            today=today,
            max_weight=max_weight,
        )
        per_row_flags.append(flags)

    page_signatures = []
    for r in rows_data:
        n_id = r.get("nasabah_id")
        w_id = r.get("waste_type_id")
        wt = r.get("weight_kg")
        dt = r.get("tanggal")
        if n_id and w_id and wt and dt:
            page_signatures.append((n_id, w_id, wt, dt))
        else:
            page_signatures.append(None)

    counts = Counter(sig for sig in page_signatures if sig is not None)
    for idx, sig in enumerate(page_signatures):
        if sig is not None and counts[sig] > 1:
            per_row_flags[idx].append({"code": "DUPLICATE_IN_PAGE", "severity": "soft"})

    db_duplicate_sigs = set()
    valid_sigs = [sig for sig in page_signatures if sig is not None]
    if valid_sigs:
        nasabah_ids = {sig[0] for sig in valid_sigs}
        waste_type_ids = {sig[1] for sig in valid_sigs}
        dates = {sig[3] for sig in valid_sigs}

        existing_deposits = Deposit.objects.filter(
            bank_sampah_id=bank_id,
            deleted_at__isnull=True,
            nasabah_id__in=nasabah_ids,
            waste_type_id__in=waste_type_ids,
            deposit_date__in=dates,
        ).values_list("nasabah_id", "waste_type_id", "weight_kg", "deposit_date")

        for n_id, w_id, wt, dt in existing_deposits:
            db_duplicate_sigs.add((n_id, w_id, wt, dt))

    for idx, sig in enumerate(page_signatures):
        if sig is not None and sig in db_duplicate_sigs:
            per_row_flags[idx].append({"code": "DUPLICATE_IN_DB", "severity": "soft"})

    return [deduplicate_flags(f) for f in per_row_flags]
