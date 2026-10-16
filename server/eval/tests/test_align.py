from eval.align import align_rows


def _make_row(tanggal: str, nasabah: str, waste_type: str, weight: str) -> dict:
    return {
        "tanggal": tanggal,
        "nasabah": nasabah,
        "waste_type_code": waste_type,
        "weight_kg": weight,
    }


def test_align_exact_match():
    gold = [
        _make_row("2026-10-01", "Ambar", "kardus", "4.500"),
        _make_row("2026-10-01", "Edi", "besi", "8.000"),
        _make_row("2026-10-02", "Siti", "pet", "2.000"),
    ]
    pred = list(gold)
    aligned = align_rows(gold, pred)
    assert len(aligned) == 3
    for idx, pair in enumerate(aligned):
        assert pair.gold_index == idx
        assert pair.pred_index == idx
        assert pair.similarity == 1.0


def test_align_skipped_row_in_middle():
    gold = [
        _make_row("2026-10-01", "Ambar", "kardus", "4.500"),
        _make_row("2026-10-01", "Edi", "besi", "8.000"),
        _make_row("2026-10-02", "Siti", "pet", "2.000"),
    ]
    pred = [
        _make_row("2026-10-01", "Ambar", "kardus", "4.500"),
        _make_row("2026-10-02", "Siti", "pet", "2.000"),
    ]
    aligned = align_rows(gold, pred)
    assert len(aligned) == 3
    assert aligned[0].gold_index == 0 and aligned[0].pred_index == 0
    assert aligned[1].gold_index == 1 and aligned[1].pred_index is None
    assert aligned[2].gold_index == 2 and aligned[2].pred_index == 1


def test_align_extra_row_in_middle():
    gold = [
        _make_row("2026-10-01", "Ambar", "kardus", "4.500"),
        _make_row("2026-10-02", "Siti", "pet", "2.000"),
    ]
    pred = [
        _make_row("2026-10-01", "Ambar", "kardus", "4.500"),
        _make_row("2026-10-09", "Hantu", "kaca", "99.000"),
        _make_row("2026-10-02", "Siti", "pet", "2.000"),
    ]
    aligned = align_rows(gold, pred)
    assert len(aligned) == 3
    assert aligned[0].gold_index == 0 and aligned[0].pred_index == 0
    assert aligned[1].gold_index is None and aligned[1].pred_index == 1
    assert aligned[2].gold_index == 1 and aligned[2].pred_index == 2


def test_align_two_swapped_rows():
    gold = [
        _make_row("2026-10-01", "Ambar", "kardus", "4.500"),
        _make_row("2026-10-01", "Edi", "besi", "8.000"),
        _make_row("2026-10-02", "Siti", "pet", "2.000"),
    ]
    pred = [
        _make_row("2026-10-01", "Edi", "besi", "8.000"),
        _make_row("2026-10-01", "Ambar", "kardus", "4.500"),
        _make_row("2026-10-02", "Siti", "pet", "2.000"),
    ]
    aligned = align_rows(gold, pred)
    matched = [p for p in aligned if p.gold_index is not None and p.pred_index is not None]
    assert len(matched) == 3
    gold_to_pred = {p.gold_index: p.pred_index for p in matched}
    assert gold_to_pred == {0: 1, 1: 0, 2: 2}
