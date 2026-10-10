from datetime import date
from decimal import Decimal

from ingestion.services.score import compute_row_score, route_row


def test_score_calculation():
    score = compute_row_score(
        llm_confidence=1.0,
        type_score=1.0,
        name_score=1.0,
        weight_kg=Decimal("2.500"),
        date_val=date(2026, 10, 1),
        date_quality="explicit",
        flags=[],
    )
    assert score == 1.0


def test_score_with_assumed_unit_and_inferred_date():
    score = compute_row_score(
        llm_confidence=1.0,
        type_score=1.0,
        name_score=1.0,
        weight_kg=Decimal("2.500"),
        date_val=date(2026, 10, 1),
        date_quality="inferred",
        flags=[{"code": "UNIT_ASSUMED_KG", "severity": "soft"}],
    )
    expected = 0.20 * 1.0 + 0.25 * 1.0 + 0.20 * 1.0 + 0.25 * 0.7 + 0.10 * 0.8
    assert round(score, 4) == round(expected, 4)


def test_routing_hard_flag_forces_manual_at_high_score():
    route = route_row(
        score=0.99,
        flags=[{"code": "TYPE_UNKNOWN", "severity": "hard"}],
        auto_save_enabled=True,
    )
    assert route == "manual"


def test_routing_auto_save_disabled_routes_to_confirm():
    route = route_row(
        score=0.95,
        flags=[],
        auto_save_enabled=False,
    )
    assert route == "confirm"


def test_routing_soft_flag_blocks_auto():
    route = route_row(
        score=0.95,
        flags=[{"code": "UNIT_ASSUMED_KG", "severity": "soft"}],
        auto_save_enabled=True,
    )
    assert route == "confirm"


def test_routing_low_score_routes_to_manual():
    route = route_row(
        score=0.55,
        flags=[],
        auto_save_enabled=True,
    )
    assert route == "manual"


def test_routing_auto_save_enabled_routes_to_auto():
    route = route_row(
        score=0.95,
        flags=[],
        auto_save_enabled=True,
    )
    assert route == "auto"
