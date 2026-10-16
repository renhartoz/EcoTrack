from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from ingestion.services.normalize import normalize_text


@dataclass(frozen=True)
class AlignedPair:
    gold_index: int | None
    pred_index: int | None
    gold_row: dict[str, Any] | None
    pred_row: dict[str, Any] | None
    similarity: float


def _to_decimal(val: Any) -> Decimal | None:
    if val is None or val == "":
        return None
    try:
        return Decimal(str(val)).quantize(Decimal("0.001"))
    except Exception:
        return None


def field_matches(gold_row: dict[str, Any], pred_row: dict[str, Any]) -> dict[str, bool]:
    g_date = str(gold_row.get("tanggal")) if gold_row.get("tanggal") is not None else None
    p_date = str(pred_row.get("tanggal")) if pred_row.get("tanggal") is not None else None
    tanggal_exact = g_date == p_date

    g_name = normalize_text(gold_row.get("nasabah"))
    p_name = normalize_text(pred_row.get("nasabah"))
    nasabah_exact = bool(g_name and g_name == p_name) or (not g_name and not p_name)

    g_type = gold_row.get("waste_type_code")
    p_type = pred_row.get("waste_type_code")
    waste_type_exact = g_type == p_type

    g_wt = _to_decimal(gold_row.get("weight_kg"))
    p_wt = _to_decimal(pred_row.get("weight_kg"))
    weight_exact = g_wt == p_wt
    if g_wt is None and p_wt is None:
        weight_within_01 = True
    elif g_wt is not None and p_wt is not None:
        weight_within_01 = abs(g_wt - p_wt) <= Decimal("0.100")
    else:
        weight_within_01 = False

    row_exact = tanggal_exact and nasabah_exact and waste_type_exact and weight_exact

    return {
        "tanggal_exact": tanggal_exact,
        "nasabah_exact": nasabah_exact,
        "waste_type_exact": waste_type_exact,
        "weight_exact": weight_exact,
        "weight_within_01": weight_within_01,
        "row_exact": row_exact,
    }


def row_similarity(gold_row: dict[str, Any], pred_row: dict[str, Any]) -> float:
    matches = field_matches(gold_row, pred_row)
    score = 0.0
    if matches["tanggal_exact"]:
        score += 0.25
    if matches["nasabah_exact"]:
        score += 0.25
    if matches["waste_type_exact"]:
        score += 0.25
    if matches["weight_exact"]:
        score += 0.25
    elif matches["weight_within_01"]:
        score += 0.15
    return round(score, 4)


def align_rows(
    gold_rows: list[dict[str, Any]],
    pred_rows: list[dict[str, Any]],
    gap_penalty: float = -0.10,
    min_similarity: float = 0.25,
) -> list[AlignedPair]:
    m = len(gold_rows)
    n = len(pred_rows)

    dp = [[0.0] * (n + 1) for _ in range(m + 1)]
    back: list[list[str]] = [[""] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        dp[i][0] = i * gap_penalty
        back[i][0] = "up"
    for j in range(1, n + 1):
        dp[0][j] = j * gap_penalty
        back[0][j] = "left"

    sim_matrix = [[0.0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            sim_matrix[i][j] = row_similarity(gold_rows[i], pred_rows[j])

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            sim = sim_matrix[i - 1][j - 1]
            pair_score = sim if sim >= min_similarity else -1.0
            diag = dp[i - 1][j - 1] + pair_score
            up = dp[i - 1][j] + gap_penalty
            left = dp[i][j - 1] + gap_penalty

            if diag >= up and diag >= left and sim >= min_similarity:
                dp[i][j] = diag
                back[i][j] = "diag"
            elif up >= left:
                dp[i][j] = up
                back[i][j] = "up"
            else:
                dp[i][j] = left
                back[i][j] = "left"

    raw_pairs: list[AlignedPair] = []
    i, j = m, n
    while i > 0 or j > 0:
        move = back[i][j]
        if i > 0 and j > 0 and move == "diag":
            sim = sim_matrix[i - 1][j - 1]
            raw_pairs.append(
                AlignedPair(
                    gold_index=i - 1,
                    pred_index=j - 1,
                    gold_row=gold_rows[i - 1],
                    pred_row=pred_rows[j - 1],
                    similarity=sim,
                )
            )
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or move == "up"):
            raw_pairs.append(
                AlignedPair(
                    gold_index=i - 1,
                    pred_index=None,
                    gold_row=gold_rows[i - 1],
                    pred_row=None,
                    similarity=0.0,
                )
            )
            i -= 1
        else:
            raw_pairs.append(
                AlignedPair(
                    gold_index=None,
                    pred_index=j - 1,
                    gold_row=None,
                    pred_row=pred_rows[j - 1],
                    similarity=0.0,
                )
            )
            j -= 1

    raw_pairs.reverse()

    unmatched_gold = [
        idx for idx, p in enumerate(raw_pairs) if p.gold_index is not None and p.pred_index is None
    ]
    unmatched_pred = [
        idx for idx, p in enumerate(raw_pairs) if p.pred_index is not None and p.gold_index is None
    ]

    used_pred_pair_indices: set[int] = set()
    replaced_gold: dict[int, AlignedPair] = {}

    for g_pair_idx in unmatched_gold:
        g_idx = raw_pairs[g_pair_idx].gold_index
        assert g_idx is not None
        best_p_pair_idx = -1
        best_sim = 0.0
        for p_pair_idx in unmatched_pred:
            if p_pair_idx in used_pred_pair_indices:
                continue
            p_idx = raw_pairs[p_pair_idx].pred_index
            assert p_idx is not None
            sim = sim_matrix[g_idx][p_idx]
            if sim > best_sim:
                best_sim = sim
                best_p_pair_idx = p_pair_idx
        if best_p_pair_idx >= 0 and best_sim >= 0.75:
            used_pred_pair_indices.add(best_p_pair_idx)
            p_idx = raw_pairs[best_p_pair_idx].pred_index
            assert p_idx is not None
            replaced_gold[g_pair_idx] = AlignedPair(
                gold_index=g_idx,
                pred_index=p_idx,
                gold_row=gold_rows[g_idx],
                pred_row=pred_rows[p_idx],
                similarity=best_sim,
            )

    final_pairs: list[AlignedPair] = []
    for idx, p in enumerate(raw_pairs):
        if idx in used_pred_pair_indices:
            continue
        if idx in replaced_gold:
            final_pairs.append(replaced_gold[idx])
        else:
            final_pairs.append(p)

    return final_pairs
