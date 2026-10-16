import statistics
from typing import Any

from eval.align import align_rows, field_matches
from ingestion.services.score import route_row


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 3)
    idx = (len(sorted_vals) - 1) * pct
    low = int(idx)
    high = min(low + 1, len(sorted_vals) - 1)
    frac = idx - low
    return round(sorted_vals[low] * (1.0 - frac) + sorted_vals[high] * frac, 3)


def evaluate_pages(
    pages_data: list[dict[str, Any]],
    t_auto: float = 0.92,
    t_confirm: float = 0.60,
) -> dict[str, Any]:
    n_gold = 0
    n_pred = 0
    n_aligned = 0
    n_row_exact = 0
    n_tanggal_exact = 0
    n_nasabah_exact = 0
    n_waste_type_exact = 0
    n_weight_exact = 0
    n_weight_within_01 = 0

    n_auto = 0
    n_confirm = 0
    n_manual = 0
    n_auto_exact = 0

    n_must_not_auto = 0
    n_unsafe_auto = 0

    latencies_s: list[float] = []
    prompt_tokens_list: list[int] = []
    completion_tokens_list: list[int] = []

    for page in pages_data:
        gold_rows = page.get("gold_rows", [])
        pred_rows = page.get("pred_rows", [])

        lat_ms = float(page.get("latency_ms", 0))
        latencies_s.append(round(lat_ms / 1000.0, 3))
        prompt_tokens_list.append(int(page.get("prompt_tokens", 0)))
        completion_tokens_list.append(int(page.get("completion_tokens", 0)))

        routed_preds: list[dict[str, Any]] = []
        for p in pred_rows:
            r_Copy = dict(p)
            r_Copy["route"] = route_row(
                score=float(p.get("score", 0.0)),
                flags=p.get("flags", []),
                auto_save_enabled=True,
                t_auto=t_auto,
                t_confirm=t_confirm,
            )
            routed_preds.append(r_Copy)

        n_gold += len(gold_rows)
        n_pred += len(routed_preds)

        for p in routed_preds:
            rt = p["route"]
            if rt == "auto":
                n_auto += 1
            elif rt == "confirm":
                n_confirm += 1
            else:
                n_manual += 1

        for g in gold_rows:
            if g.get("must_not_auto", False):
                n_must_not_auto += 1

        pairs = align_rows(gold_rows, routed_preds)
        for pair in pairs:
            g_row = pair.gold_row
            p_row = pair.pred_row
            if g_row is not None and p_row is not None:
                n_aligned += 1
                fm = field_matches(g_row, p_row)
                if fm["tanggal_exact"]:
                    n_tanggal_exact += 1
                if fm["nasabah_exact"]:
                    n_nasabah_exact += 1
                if fm["waste_type_exact"]:
                    n_waste_type_exact += 1
                if fm["weight_exact"]:
                    n_weight_exact += 1
                if fm["weight_within_01"]:
                    n_weight_within_01 += 1
                if fm["row_exact"]:
                    n_row_exact += 1
                    if p_row["route"] == "auto":
                        n_auto_exact += 1
                if g_row.get("must_not_auto", False) and p_row["route"] == "auto":
                    n_unsafe_auto += 1

    row_recall = round(n_aligned / n_gold, 4) if n_gold > 0 else 0.0
    row_precision = round(n_aligned / n_pred, 4) if n_pred > 0 else 0.0
    row_exact_rate = round(n_row_exact / n_gold, 4) if n_gold > 0 else 0.0
    tanggal_exact_rate = round(n_tanggal_exact / n_gold, 4) if n_gold > 0 else 0.0
    nasabah_exact_rate = round(n_nasabah_exact / n_gold, 4) if n_gold > 0 else 0.0
    waste_type_exact_rate = round(n_waste_type_exact / n_gold, 4) if n_gold > 0 else 0.0
    weight_exact_rate = round(n_weight_exact / n_gold, 4) if n_gold > 0 else 0.0
    weight_within_01_rate = round(n_weight_within_01 / n_gold, 4) if n_gold > 0 else 0.0

    auto_precision = round(n_auto_exact / n_auto, 4) if n_auto > 0 else 1.0
    auto_coverage = round(n_auto / n_gold, 4) if n_gold > 0 else 0.0
    unsafe_auto_rate = round(n_unsafe_auto / n_must_not_auto, 4) if n_must_not_auto > 0 else 0.0

    latency_p50_s = round(statistics.median(latencies_s), 2) if latencies_s else 0.0
    latency_p95_s = round(percentile(latencies_s, 0.95), 2) if latencies_s else 0.0
    avg_prompt_tokens = round(statistics.mean(prompt_tokens_list), 1) if prompt_tokens_list else 0.0
    avg_completion_tokens = (
        round(statistics.mean(completion_tokens_list), 1) if completion_tokens_list else 0.0
    )

    return {
        "t_auto": t_auto,
        "t_confirm": t_confirm,
        "n_pages": len(pages_data),
        "n_gold": n_gold,
        "n_pred": n_pred,
        "n_aligned": n_aligned,
        "n_row_exact": n_row_exact,
        "n_tanggal_exact": n_tanggal_exact,
        "n_nasabah_exact": n_nasabah_exact,
        "n_waste_type_exact": n_waste_type_exact,
        "n_weight_exact": n_weight_exact,
        "n_weight_within_01": n_weight_within_01,
        "n_auto": n_auto,
        "n_confirm": n_confirm,
        "n_manual": n_manual,
        "n_auto_exact": n_auto_exact,
        "n_must_not_auto": n_must_not_auto,
        "n_unsafe_auto": n_unsafe_auto,
        "row_recall": row_recall,
        "row_precision": row_precision,
        "row_exact_rate": row_exact_rate,
        "tanggal_exact_rate": tanggal_exact_rate,
        "nasabah_exact_rate": nasabah_exact_rate,
        "waste_type_exact_rate": waste_type_exact_rate,
        "weight_exact_rate": weight_exact_rate,
        "weight_within_01_rate": weight_within_01_rate,
        "auto_precision": auto_precision,
        "auto_coverage": auto_coverage,
        "unsafe_auto_rate": unsafe_auto_rate,
        "latency_p50_s": latency_p50_s,
        "latency_p95_s": latency_p95_s,
        "avg_prompt_tokens": avg_prompt_tokens,
        "avg_completion_tokens": avg_completion_tokens,
    }
