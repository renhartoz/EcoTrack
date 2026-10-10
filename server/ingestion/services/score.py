from decimal import Decimal

from django.conf import settings


def compute_row_score(
    llm_confidence: float,
    type_score: float,
    name_score: float,
    weight_kg: Decimal | None,
    date_val: object | None,
    date_quality: str,
    flags: list[dict[str, str]],
) -> float:
    w_llm = getattr(settings, "SCORE_W_LLM", 0.20)
    w_type = getattr(settings, "SCORE_W_TYPE", 0.25)
    w_name = getattr(settings, "SCORE_W_NAME", 0.20)
    w_weight = getattr(settings, "SCORE_W_WEIGHT", 0.25)
    w_date = getattr(settings, "SCORE_W_DATE", 0.10)

    s_llm = max(0.0, min(1.0, float(llm_confidence)))
    s_type = max(0.0, min(1.0, float(type_score)))
    s_name = max(0.0, min(1.0, float(name_score)))

    flag_codes = {f["code"] for f in flags}

    if (
        weight_kg is None
        or "WEIGHT_UNPARSEABLE" in flag_codes
        or "WEIGHT_NONPOSITIVE" in flag_codes
    ):
        s_weight = 0.0
    elif "UNIT_ASSUMED_KG" in flag_codes:
        s_weight = 0.7
    else:
        s_weight = 1.0

    if date_val is None or "DATE_UNPARSEABLE" in flag_codes:
        s_date = 0.0
    elif date_quality == "inherited" or "DATE_INHERITED" in flag_codes:
        s_date = 0.6
    elif date_quality == "inferred":
        s_date = 0.8
    else:
        s_date = 1.0

    score = (
        w_llm * s_llm + w_type * s_type + w_name * s_name + w_weight * s_weight + w_date * s_date
    )
    return round(float(score), 4)


def route_row(
    score: float,
    flags: list[dict[str, str]],
    auto_save_enabled: bool | None = None,
    t_auto: float | None = None,
    t_confirm: float | None = None,
) -> str:
    if auto_save_enabled is None:
        auto_save_enabled = getattr(settings, "AUTO_SAVE_ENABLED", False)
    if t_auto is None:
        t_auto = getattr(settings, "T_AUTO", 0.92)
    if t_confirm is None:
        t_confirm = getattr(settings, "T_CONFIRM", 0.60)

    if any(f.get("severity") == "hard" for f in flags):
        return "manual"
    if score >= t_auto and len(flags) == 0 and auto_save_enabled:
        return "auto"
    if score >= t_confirm:
        return "confirm"
    return "manual"
