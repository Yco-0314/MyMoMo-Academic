from abm_auto.coord._gate import CoordNullGate


def test_gate_passes_when_optimized_beats_both():
    g = CoordNullGate(margin=1.0)
    v = g.judge(original=50.0, optimized=40.0, null=49.0)  # optimized clearly best
    assert v.passed is True and v.tier == "refutation"
    assert "verified" not in v.render().lower()


def test_gate_refutes_when_optimized_ties_random():
    g = CoordNullGate(margin=1.0)
    v = g.judge(original=50.0, optimized=44.0, null=44.3)  # ~ same as random null
    assert v.passed is False
    assert v.reasons


def test_self_test():
    assert CoordNullGate().self_test() is True
