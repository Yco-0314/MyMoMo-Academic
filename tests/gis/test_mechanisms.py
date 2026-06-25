import abm_auto.gis._mechanisms as mechanisms
from abm_auto.gis._mechanisms import (
    mechanism_space_gate,
    run_contagion,
    run_threshold_adoption,
)


def _chain_neighbors(n):
    def neighbors_of(i):
        out = []
        if i > 0:
            out.append(i - 1)
        if i < n - 1:
            out.append(i + 1)
        return out

    return neighbors_of


def _isolated_neighbors(_):
    return []


def test_contagion_uses_neighbor_callable_and_is_deterministic():
    neighbors = _chain_neighbors(20)

    first = run_contagion(20, neighbors, beta=0.5, steps=8, seed=4, seeds=(0,))
    second = run_contagion(20, neighbors, beta=0.5, steps=8, seed=4, seeds=(0,))

    assert first["history"] == second["history"]
    assert first["final"] > first["history"][0]
    assert first["n_agents"] == 20


def test_contagion_requires_probability_beta():
    for beta in (-0.1, 1.1, True, "0.5"):
        try:
            run_contagion(3, _chain_neighbors(3), beta=beta)
        except ValueError as exc:
            assert "beta" in str(exc)
        else:
            raise AssertionError(f"beta={beta!r} should fail")


def test_mechanism_contagion_gate_passes_for_default_chain_neighbors():
    ok, desc = mechanisms.mechanism_contagion_gate()

    assert ok, desc
    assert "neighbor seam controls contagion" in desc
    assert "not spatial validation" in desc


def test_mechanism_contagion_gate_fails_when_connected_neighbors_are_empty():
    ok, desc = mechanisms.mechanism_contagion_gate(
        connected_neighbors_of=_isolated_neighbors,
        isolated_neighbors_of=_isolated_neighbors,
    )

    assert not ok
    assert "no connected-neighbor contagion spread" in desc


def test_mechanism_contagion_gate_fails_when_isolated_neighbors_spread():
    ok, desc = mechanisms.mechanism_contagion_gate(
        isolated_neighbors_of=_chain_neighbors(8),
    )

    assert not ok
    assert "isolated neighbors changed contagion" in desc


def test_threshold_adoption_spreads_on_connected_neighbors():
    result = run_threshold_adoption(
        6,
        _chain_neighbors(6),
        threshold=1,
        steps=5,
        seeds=(0,),
    )

    assert result["history"] == [1, 2, 3, 4, 5, 6]
    assert result["final"] == 6
    assert result["adopted"] == [True, True, True, True, True, True]


def test_threshold_adoption_stays_local_on_isolated_neighbors():
    result = run_threshold_adoption(
        6,
        _isolated_neighbors,
        threshold=1,
        steps=5,
        seeds=(0,),
    )

    assert result["history"] == [1, 1, 1, 1, 1, 1]
    assert result["final"] == 1
    assert result["adopted"] == [True, False, False, False, False, False]


def test_threshold_adoption_requires_positive_threshold():
    try:
        run_threshold_adoption(3, _chain_neighbors(3), threshold=0)
    except ValueError as exc:
        assert "threshold" in str(exc)
    else:
        raise AssertionError("threshold=0 should fail")


def test_mechanism_space_gate_passes_for_connected_vs_isolated_neighbors():
    ok, desc = mechanism_space_gate()

    assert ok, desc
    assert "neighbor seam" in desc


def test_mechanism_space_gate_materializes_seed_iterables_for_both_runs():
    ok, desc = mechanism_space_gate(seeds=(i for i in [0]))

    assert ok, desc
    assert "connected 8 vs isolated 1" in desc


def test_mechanism_space_gate_counts_duplicate_seed_ids_once():
    ok, desc = mechanism_space_gate(seeds=(0, 0))

    assert ok, desc
    assert "connected 8 vs isolated 1" in desc


def test_mechanism_space_gate_fails_when_connected_has_no_effect():
    ok, desc = mechanism_space_gate(
        connected_neighbors_of=_isolated_neighbors,
        isolated_neighbors_of=_isolated_neighbors,
    )

    assert not ok
    assert "no connected-neighbor spread" in desc
