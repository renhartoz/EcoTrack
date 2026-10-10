import re
import unicodedata
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

try:
    from rapidfuzz import fuzz, process
except ImportError:
    import difflib

    class _FuzzFallback:
        @staticmethod
        def WRatio(s1, s2):
            return difflib.SequenceMatcher(None, s1, s2).ratio() * 100.0

    class _ProcessFallback:
        @staticmethod
        def extract(query, choices, scorer=None, limit=3):
            scores = []
            for idx, choice in enumerate(choices):
                score = difflib.SequenceMatcher(None, query, choice).ratio() * 100.0
                scores.append((choice, score, idx))
            scores.sort(key=lambda x: x[1], reverse=True)
            return scores[:limit]

    fuzz = _FuzzFallback()
    process = _ProcessFallback()


HONORIFICS = {
    "bu",
    "ibu",
    "pak",
    "bpk",
    "bapak",
    "mas",
    "mbak",
    "kak",
    "h",
    "hj",
}

GRAM_UNITS = {"g", "gr", "gram"}
ONS_UNITS = {"ons"}
KG_UNITS = {"kg", "kilo", "kilogram", "kgs"}
KW_UNITS = {"kw", "kwintal"}
TON_UNITS = {"ton"}

MONTH_MAP = {
    "jan": 1,
    "januari": 1,
    "january": 1,
    "feb": 2,
    "februari": 2,
    "february": 2,
    "mar": 3,
    "maret": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "mei": 5,
    "may": 5,
    "jun": 6,
    "juni": 6,
    "june": 6,
    "jul": 7,
    "juli": 7,
    "july": 7,
    "agu": 8,
    "agt": 8,
    "agus": 8,
    "agustus": 8,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "okt": 10,
    "oktober": 10,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "des": 12,
    "desember": 12,
    "dec": 12,
    "december": 12,
}


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("utf-8")
    cleaned = re.sub(r"[^\w\s]", " ", ascii_text.lower())
    return " ".join(cleaned.split())


def strip_honorifics(nama: str | None) -> str:
    if not nama:
        return ""
    cleaned = normalize_text(nama)
    tokens = cleaned.split()
    while tokens and tokens[0] in HONORIFICS:
        tokens.pop(0)
    while tokens and tokens[-1] in HONORIFICS:
        tokens.pop()
    return " ".join(tokens)


def parse_weight(
    berat_raw: str | None,
    satuan_raw: str | None = None,
    default_unit_raw: str | None = None,
) -> tuple[Decimal | None, list[dict[str, str]]]:
    if not berat_raw or not berat_raw.strip():
        return None, [{"code": "WEIGHT_UNPARSEABLE", "severity": "hard"}]

    clean_raw = berat_raw.strip()
    if "/" in clean_raw:
        return None, [{"code": "WEIGHT_UNPARSEABLE", "severity": "hard"}]

    num_tokens = re.findall(r"\d+(?:[.,]\d+)*", clean_raw)
    if len(num_tokens) >= 2:
        return None, [
            {"code": "WEIGHT_UNPARSEABLE", "severity": "hard"},
            {"code": "CORRECTION_PRESENT", "severity": "soft"},
        ]
    if len(num_tokens) == 0:
        return None, [{"code": "WEIGHT_UNPARSEABLE", "severity": "hard"}]

    unit_str = None
    assumed_kg = False

    if satuan_raw and satuan_raw.strip():
        unit_str = satuan_raw.strip().lower()
    else:
        trailing_unit_match = re.search(r"([a-zA-Z]+)\s*$", clean_raw)
        if trailing_unit_match:
            unit_str = trailing_unit_match.group(1).lower()
        elif default_unit_raw and default_unit_raw.strip():
            unit_str = default_unit_raw.strip().lower()
        else:
            unit_str = "kg"
            assumed_kg = True

    multiplier = Decimal("1")
    unit_norm = normalize_text(unit_str)
    if unit_norm in GRAM_UNITS:
        multiplier = Decimal("0.001")
    elif unit_norm in ONS_UNITS:
        multiplier = Decimal("0.1")
    elif unit_norm in KG_UNITS:
        multiplier = Decimal("1")
    elif unit_norm in KW_UNITS:
        multiplier = Decimal("100")
    elif unit_norm in TON_UNITS:
        multiplier = Decimal("1000")
    else:
        multiplier = Decimal("1")
        assumed_kg = True

    token = num_tokens[0]
    has_dot = "." in token
    has_comma = "," in token

    if has_dot and has_comma:
        last_dot = token.rfind(".")
        last_comma = token.rfind(",")
        if last_comma > last_dot:
            sanitized = token.replace(".", "").replace(",", ".")
        else:
            sanitized = token.replace(",", "")
    elif has_dot or has_comma:
        sep = "." if has_dot else ","
        parts = token.split(sep)
        if len(parts) == 2 and len(parts[1]) == 3 and unit_norm in GRAM_UNITS:
            sanitized = parts[0] + parts[1]
        elif len(parts) > 2 and unit_norm in GRAM_UNITS and all(len(p) == 3 for p in parts[1:]):
            sanitized = "".join(parts)
        else:
            sanitized = token.replace(",", ".")
    else:
        sanitized = token

    try:
        val = Decimal(sanitized)
    except Exception:
        return None, [{"code": "WEIGHT_UNPARSEABLE", "severity": "hard"}]

    weight_kg = (val * multiplier).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    if weight_kg <= Decimal("0"):
        return None, [{"code": "WEIGHT_NONPOSITIVE", "severity": "hard"}]

    flags: list[dict[str, str]] = []
    if assumed_kg:
        flags.append({"code": "UNIT_ASSUMED_KG", "severity": "soft"})

    return weight_kg, flags


def _extract_year_from_text(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"\b(20\d\d)\b", text)
    if match:
        return int(match.group(1))
    return None


def parse_date(
    tanggal_raw: str | None,
    page_date_raw: str | None = None,
    upload_year: int = 2026,
    date_is_repeat: bool = False,
    previous_date: date | None = None,
) -> tuple[date | None, str, list[dict[str, str]]]:
    if date_is_repeat or not tanggal_raw or not tanggal_raw.strip():
        if previous_date is not None:
            return (
                previous_date,
                "inherited",
                [{"code": "DATE_INHERITED", "severity": "soft"}],
            )
        return None, "unparseable", [{"code": "DATE_UNPARSEABLE", "severity": "hard"}]

    cleaned = tanggal_raw.strip()
    page_year = _extract_year_from_text(page_date_raw)
    fallback_year = page_year if page_year is not None else upload_year

    match_dmy = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})$", cleaned)
    if match_dmy:
        day = int(match_dmy.group(1))
        month = int(match_dmy.group(2))
        year_str = match_dmy.group(3)
        year = int(year_str) if len(year_str) == 4 else 2000 + int(year_str)
        try:
            parsed = date(year, month, day)
            return parsed, "explicit", []
        except ValueError:
            return None, "unparseable", [{"code": "DATE_UNPARSEABLE", "severity": "hard"}]

    match_dm = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})$", cleaned)
    if match_dm:
        day = int(match_dm.group(1))
        month = int(match_dm.group(2))
        try:
            parsed = date(fallback_year, month, day)
            return parsed, "inferred", []
        except ValueError:
            return None, "unparseable", [{"code": "DATE_UNPARSEABLE", "severity": "hard"}]

    tokens = cleaned.replace("/", " ").replace("-", " ").replace(".", " ").split()
    if len(tokens) >= 2 and tokens[0].isdigit():
        day = int(tokens[0])
        m_str = tokens[1].lower()
        if m_str in MONTH_MAP:
            month = MONTH_MAP[m_str]
            year = fallback_year
            quality = "inferred"
            if len(tokens) >= 3 and tokens[2].isdigit():
                y_val = int(tokens[2])
                year = y_val if y_val >= 1000 else 2000 + y_val
                quality = "explicit"
            try:
                parsed = date(year, month, day)
                return parsed, quality, []
            except ValueError:
                return None, "unparseable", [{"code": "DATE_UNPARSEABLE", "severity": "hard"}]

    return None, "unparseable", [{"code": "DATE_UNPARSEABLE", "severity": "hard"}]


def match_waste_type(
    jenis_raw: str | None,
    candidates: list[tuple[int, str, list[str]]],
    min_score: float = 0.75,
    ambiguity_margin: float = 0.05,
) -> tuple[int | None, float, list[dict[str, str]]]:
    if not jenis_raw or not jenis_raw.strip():
        return None, 0.0, [{"code": "TYPE_UNKNOWN", "severity": "hard"}]

    norm = normalize_text(jenis_raw)
    if not norm:
        return None, 0.0, [{"code": "TYPE_UNKNOWN", "severity": "hard"}]

    for type_id, name_id, aliases in candidates:
        if norm == normalize_text(name_id):
            return type_id, 1.0, []
        for alias in aliases:
            if norm == normalize_text(alias):
                return type_id, 1.0, []

    flat_choices: list[str] = []
    choice_type_map: dict[str, int] = {}
    for type_id, name_id, aliases in candidates:
        name_norm = normalize_text(name_id)
        if name_norm and name_norm not in choice_type_map:
            flat_choices.append(name_norm)
            choice_type_map[name_norm] = type_id
        for alias in aliases:
            alias_norm = normalize_text(alias)
            if alias_norm and alias_norm not in choice_type_map:
                flat_choices.append(alias_norm)
                choice_type_map[alias_norm] = type_id

    if not flat_choices:
        return None, 0.0, [{"code": "TYPE_UNKNOWN", "severity": "hard"}]

    extracted = process.extract(norm, flat_choices, scorer=fuzz.WRatio, limit=3)
    if not extracted:
        return None, 0.0, [{"code": "TYPE_UNKNOWN", "severity": "hard"}]

    best_match_text, best_raw_score, _ = extracted[0]
    best_score = float(best_raw_score) / 100.0
    best_type_id = choice_type_map[best_match_text]

    if best_score < min_score:
        return None, best_score, [{"code": "TYPE_UNKNOWN", "severity": "hard"}]

    if len(extracted) > 1:
        second_match_text, second_raw_score, _ = extracted[1]
        second_score = float(second_raw_score) / 100.0
        second_type_id = choice_type_map[second_match_text]
        if second_type_id != best_type_id and (best_score - second_score) < ambiguity_margin:
            return (
                best_type_id,
                best_score,
                [{"code": "AMBIGUOUS_TYPE", "severity": "soft"}],
            )

    return best_type_id, best_score, []


def match_nasabah(
    nama_raw: str | None,
    nasabah_candidates: list[tuple[int, str]],
    min_score: float = 0.85,
    ambiguity_margin: float = 0.05,
) -> tuple[int | None, float, list[dict[str, str]]]:
    if not nama_raw or not nama_raw.strip():
        return None, 0.0, [{"code": "NASABAH_UNKNOWN", "severity": "hard"}]

    stripped = strip_honorifics(nama_raw)
    if not stripped:
        return None, 0.0, [{"code": "NASABAH_UNKNOWN", "severity": "hard"}]

    for nasabah_id, norm_name in nasabah_candidates:
        if stripped == norm_name:
            return nasabah_id, 1.0, []

    flat_names = [c[1] for c in nasabah_candidates]
    id_map = {c[1]: c[0] for c in nasabah_candidates}

    if not flat_names:
        return None, 0.0, [{"code": "NASABAH_UNKNOWN", "severity": "hard"}]

    extracted = process.extract(stripped, flat_names, scorer=fuzz.WRatio, limit=3)
    if not extracted:
        return None, 0.0, [{"code": "NASABAH_UNKNOWN", "severity": "hard"}]

    best_name, best_raw_score, _ = extracted[0]
    best_score = float(best_raw_score) / 100.0
    best_nasabah_id = id_map[best_name]

    if best_score < min_score:
        return None, best_score, [{"code": "NASABAH_UNKNOWN", "severity": "hard"}]

    if len(extracted) > 1:
        second_name, second_raw_score, _ = extracted[1]
        second_score = float(second_raw_score) / 100.0
        second_nasabah_id = id_map[second_name]
        if second_nasabah_id != best_nasabah_id and (best_score - second_score) < ambiguity_margin:
            return (
                best_nasabah_id,
                best_score,
                [{"code": "AMBIGUOUS_NASABAH", "severity": "soft"}],
            )

    return best_nasabah_id, best_score, []
