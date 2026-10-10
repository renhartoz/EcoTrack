from datetime import date
from decimal import Decimal

from ingestion.services.normalize import (
    match_nasabah,
    match_waste_type,
    parse_date,
    parse_weight,
    strip_honorifics,
)


def test_weight_table_spec_14():
    cases = [
        ("2,5", "kg", Decimal("2.500"), []),
        ("2.5", "kg", Decimal("2.500"), []),
        ("500", "g", Decimal("0.500"), []),
        ("1.500", "gr", Decimal("1.500"), []),
        ("2", "ons", Decimal("0.200"), []),
        ("1", "kw", Decimal("100.000"), []),
        ("0,5", "ton", Decimal("500.000"), []),
        ("1.234,5", "kg", Decimal("1234.500"), []),
        ("2,5", None, Decimal("2.500"), [{"code": "UNIT_ASSUMED_KG", "severity": "soft"}]),
        ("2,5kg", None, Decimal("2.500"), []),
        ("abc", "kg", None, [{"code": "WEIGHT_UNPARSEABLE", "severity": "hard"}]),
        ("1/2", "kg", None, [{"code": "WEIGHT_UNPARSEABLE", "severity": "hard"}]),
        ("0", "kg", None, [{"code": "WEIGHT_NONPOSITIVE", "severity": "hard"}]),
        ("1", "pcs", None, [{"code": "WEIGHT_UNPARSEABLE", "severity": "hard"}]),
    ]

    for berat_raw, satuan_raw, expected_val, expected_flags in cases:
        val, flags = parse_weight(berat_raw, satuan_raw)
        assert val == expected_val, f"Failed on berat={berat_raw}, satuan={satuan_raw}"
        assert flags == expected_flags, f"Flags mismatch on berat={berat_raw}, satuan={satuan_raw}"


def test_weight_multiple_numbers_adds_correction_flag():
    val, flags = parse_weight("6kg, 5kg", "kg")
    assert val is None
    codes = {f["code"] for f in flags}
    assert "WEIGHT_UNPARSEABLE" in codes
    assert "CORRECTION_PRESENT" in codes


def test_weight_page_default_unit():
    val, flags = parse_weight("500", None, default_unit_raw="gr")
    assert val == Decimal("0.500")
    assert flags == []


def test_dates_spec_14():
    d1, q1, f1 = parse_date("12/9", page_date_raw="September 2026", upload_year=2026)
    assert d1 == date(2026, 9, 12)
    assert q1 == "inferred"
    assert f1 == []

    d2, q2, f2 = parse_date("12-09-26", page_date_raw=None, upload_year=2026)
    assert d2 == date(2026, 9, 12)
    assert q2 == "explicit"
    assert f2 == []

    d3, q3, f3 = parse_date("5 Okt", page_date_raw=None, upload_year=2026)
    assert d3 == date(2026, 10, 5)
    assert q3 == "inferred"
    assert f3 == []

    d4, q4, f4 = parse_date("5 Oct", page_date_raw=None, upload_year=2026)
    assert d4 == date(2026, 10, 5)
    assert q4 == "inferred"
    assert f4 == []

    prev = date(2026, 9, 12)
    d5, q5, f5 = parse_date("", date_is_repeat=True, previous_date=prev)
    assert d5 == prev
    assert q5 == "inherited"
    assert any(f["code"] == "DATE_INHERITED" for f in f5)

    d6, q6, f6 = parse_date("", date_is_repeat=True, previous_date=None)
    assert d6 is None
    assert q6 == "unparseable"
    assert any(f["code"] == "DATE_UNPARSEABLE" for f in f6)


def test_matching_waste_types_spec_14():
    candidates = [
        (1, "Plastik PET (botol)", ["botol", "botol plastik", "pet", "botol aqua", "botol minum"]),
        (2, "Kardus", ["kardus", "dus", "karton"]),
        (3, "Besi dan logam", ["besi", "logam", "besi tua"]),
    ]

    t1, s1, f1 = match_waste_type("botol aqua", candidates)
    assert t1 == 1
    assert s1 == 1.0
    assert f1 == []

    t2, s2, f2 = match_waste_type("dus", candidates)
    assert t2 == 2
    assert s2 == 1.0
    assert f2 == []

    t3, s3, f3 = match_waste_type("xyz unrelated garbage text", candidates)
    assert t3 is None
    assert any(f["code"] == "TYPE_UNKNOWN" for f in f3)


def test_matching_nasabah_spec_14():
    candidates = [
        (1, "siti"),
        (2, "bambang"),
    ]

    n1, s1, f1 = match_nasabah("Bu Siti", candidates)
    assert n1 == 1
    assert s1 == 1.0
    assert f1 == []

    n2, s2, f2 = match_nasabah("Pak Bambang", candidates)
    assert n2 == 2
    assert s2 == 1.0
    assert f2 == []

    n3, s3, f3 = match_nasabah("Orang Asing Sekali", candidates)
    assert n3 is None
    assert any(f["code"] == "NASABAH_UNKNOWN" for f in f3)


def test_matching_ambiguous_nasabah():
    candidates = [
        (1, "siti aminah"),
        (2, "siti amalia"),
    ]

    n, s, f = match_nasabah("Siti Am", candidates, ambiguity_margin=0.20)
    assert any(f_item["code"] == "AMBIGUOUS_NASABAH" for f_item in f)


def test_honorific_stripping():
    assert strip_honorifics("Bu Siti") == "siti"
    assert strip_honorifics("Pak Bambang") == "bambang"
    assert strip_honorifics("Ibu Siti") == "siti"
    assert strip_honorifics("Mas Danu") == "danu"
    assert strip_honorifics("Mbak Rina") == "rina"
    assert strip_honorifics("Haji Joko") == "haji joko"
    assert strip_honorifics("H. Joko") == "joko"
