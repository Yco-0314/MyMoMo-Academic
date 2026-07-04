"""Faithful-rule + determinism tests for the Axelrod (1986) Norms / Metanorms
reproduction.

These pin the payoff bookkeeping for hand-built scenarios (a defection: defector +T,
others −H; a punishment: defector −E, punisher −P; a metanorm meta-punishment:
non-punisher −E', meta-punisher −P'), the defect rule (b > S), the fact that the
metanorm flag changes ONLY the meta-punishment step, Axelrod's selection rule and the
gene-bounded mutation ({0..7}), determinism (same seed → identical), and that the two
arms are bit-identical when metanorms are off.

They are FAITHFULNESS tests, NOT prediction tests — the locked predictions P1-P3 are
evaluated by examples/repro_axelrod_norms/run.py.
"""
from __future__ import annotations

import random

import pytest

from abm_auto.classics.axelrod_norms import (
    GENE_MAX,
    NormsModel,
    PlayerAgent,
    run_single,
    run_many_seeds,
    tail_mean,
)


# -- a scripted RNG to drive hand-built scenarios -----------------------------

class ScriptedRandom(random.Random):
    """A Random whose ``random()`` returns a pre-set queue of values (then a default),
    so a test can dictate exactly which draws happen (S values, see-rolls, punish-rolls,
    meta-rolls). ``randint``/``randrange`` fall back to the base implementation (seeded),
    which is only used during population construction in these tests."""

    def __init__(self, queue, *, default: float = 0.0, seed: int = 0) -> None:
        super().__init__(seed)
        self._queue = list(queue)
        self._default = default

    def random(self) -> float:  # type: ignore[override]
        if self._queue:
            return self._queue.pop(0)
        return self._default


def _two_player_model(*, metanorms: bool, B0, V0, B1, V1) -> NormsModel:
    """A 2-agent model with explicitly set genes (construction RNG is irrelevant; we
    overwrite the genes), ready for a scripted round."""
    m = NormsModel(n=2, metanorms=metanorms, rounds_per_gen=1, mut_rate=0.0,
                   n_generations=0, seed=0)
    m.agent_list[0].B, m.agent_list[0].V = B0, V0
    m.agent_list[1].B, m.agent_list[1].V = B1, V1
    for a in m.agent_list:
        a.payoff = 0.0
    return m


# -- gene normalisation + construction ----------------------------------------

def test_genes_normalise_to_unit_interval():
    a = PlayerAgent(0, _two_player_model(metanorms=False, B0=7, V0=0, B1=0, V1=7), B=7, V=0)
    assert a.b == pytest.approx(1.0)
    assert a.v == pytest.approx(0.0)
    b = PlayerAgent(1, a.model, B=0, V=7)
    assert b.b == pytest.approx(0.0)
    assert b.v == pytest.approx(1.0)


def test_population_genes_in_range():
    m = NormsModel(n=20, seed=3)
    assert len(m.agent_list) == 20
    for a in m.agent_list:
        assert isinstance(a, PlayerAgent)
        assert 0 <= a.B <= GENE_MAX and 0 <= a.V <= GENE_MAX


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        NormsModel(n=1)                       # need n > 1
    with pytest.raises(ValueError):
        NormsModel(n=20, rounds_per_gen=0)
    with pytest.raises(ValueError):
        NormsModel(n=20, mut_rate=1.5)
    with pytest.raises(ValueError):
        PlayerAgent(0, NormsModel(n=2, seed=0), B=8, V=0)   # gene out of range


# -- the defect rule: b > S ---------------------------------------------------

def test_defect_iff_boldness_exceeds_S():
    # Actor (agent 0) has B=7 -> b=1.0; the other agent is meek (V=0, never punishes).
    # With S = 0.5 < b, the actor DEFECTS: +T to it, -H to the other. No one punishes.
    m = _two_player_model(metanorms=False, B0=7, V0=0, B1=0, V1=0)
    # Round draws (in order): S for actor0 (=0.5 -> defect), see-roll for the other
    # (>=S so it does NOT see), then S for actor1 (=0.9; its b=0 so no defection, and we
    # never reach a see-roll).
    m.rng = ScriptedRandom([0.5, 0.9, 0.9])
    m.play_round()
    assert m.agent_list[0].payoff == pytest.approx(m.T)        # +T
    assert m.agent_list[1].payoff == pytest.approx(-m.H)       # -H


def test_no_defection_when_boldness_below_S():
    # Actor boldness b = 0 (B=0); for any S in (0,1], b <= S so it never defects.
    m = _two_player_model(metanorms=False, B0=0, V0=0, B1=0, V1=0)
    m.rng = ScriptedRandom([0.5, 0.5])        # S for each actor; neither defects
    m.play_round()
    assert m.agent_list[0].payoff == pytest.approx(0.0)
    assert m.agent_list[1].payoff == pytest.approx(0.0)


# -- payoff bookkeeping: defection + punishment -------------------------------

def test_defection_gives_T_to_defector_and_minus_H_to_others():
    # 3 agents; only agent 0 is bold (B=7). Others have V=0 so even if they see, they
    # never punish — isolating the T / H bookkeeping.
    m = NormsModel(n=3, metanorms=False, rounds_per_gen=1, mut_rate=0.0,
                   n_generations=0, seed=0)
    for a in m.agent_list:
        a.payoff = 0.0
    m.agent_list[0].B, m.agent_list[0].V = 7, 0
    m.agent_list[1].B, m.agent_list[1].V = 0, 0
    m.agent_list[2].B, m.agent_list[2].V = 0, 0
    # Draws: S0=0.5 (agent0 defects); see-roll agent1 (0.4 < S -> sees, but V=0 so the
    # punish-roll is never taken); see-roll agent2 (0.9 -> does not see). Then S1=0.9,
    # S2=0.9 (no defection from the meek agents).
    m.rng = ScriptedRandom([0.5, 0.4, 0.9, 0.9, 0.9])
    m.play_round()
    assert m.agent_list[0].payoff == pytest.approx(m.T)            # defector +T only
    assert m.agent_list[1].payoff == pytest.approx(-m.H)           # hurt, no punish cost
    assert m.agent_list[2].payoff == pytest.approx(-m.H)


def test_punishment_costs_E_to_defector_and_P_to_punisher():
    # 2 agents. Agent0 bold (B=7) defects; agent1 maximally vengeful (V=7) sees + punishes.
    m = _two_player_model(metanorms=False, B0=7, V0=0, B1=0, V1=7)
    # S0=0.5 (defect); see-roll agent1 = 0.1 (< S -> sees); punish-roll = 0.1 (< v=1 ->
    # punishes). Then S1=0.9 (agent1 b=0, no defection).
    m.rng = ScriptedRandom([0.5, 0.1, 0.1, 0.9])
    m.play_round()
    # defector: +T (defect) - E (punished); punisher: -H (hurt) - P (enforcement cost).
    assert m.agent_list[0].payoff == pytest.approx(m.T - m.E)
    assert m.agent_list[1].payoff == pytest.approx(-m.H - m.P)


def test_seer_with_zero_vengefulness_does_not_punish():
    # Agent1 sees (see-roll < S) but V=0 -> the punish-roll prob is 0, so no punishment.
    m = _two_player_model(metanorms=False, B0=7, V0=0, B1=0, V1=0)
    m.rng = ScriptedRandom([0.5, 0.1, 0.99, 0.9])   # S, see(<S), punish-roll, S1
    m.play_round()
    assert m.agent_list[0].payoff == pytest.approx(m.T)     # not punished
    assert m.agent_list[1].payoff == pytest.approx(-m.H)    # only hurt


# -- the metanorm step (the ONLY arm difference) ------------------------------

def test_metanorm_meta_punishes_a_nonpunisher():
    # 3 agents. Agent0 bold (B=7) defects. Agent1 SEES but does NOT punish (V=0 -> a
    # non-punisher). Agent2 is the meta-punisher (V=7). With metanorms ON, agent2
    # meta-punishes agent1: agent1 -E', agent2 -P'.
    m = NormsModel(n=3, metanorms=True, rounds_per_gen=1, mut_rate=0.0,
                   n_generations=0, seed=0)
    for a in m.agent_list:
        a.payoff = 0.0
    m.agent_list[0].B, m.agent_list[0].V = 7, 0     # bold defector, never punishes
    m.agent_list[1].B, m.agent_list[1].V = 0, 0     # sees, V=0 -> NON-punisher
    m.agent_list[2].B, m.agent_list[2].V = 0, 7     # the avenger of non-punishment
    # Draws for the defection by agent0 (S0=0.5):
    #   see-roll agent1 = 0.1 (<S -> sees); punish-roll = 0.9 (>=v=0 -> does NOT punish,
    #     so agent1 is a non-punisher). NOTE: the punish-roll is drawn whenever a seer
    #     sees, regardless of v.
    #   see-roll agent2 = 0.9 (>=S -> agent2 does NOT see the defection itself).
    # Metanorm step: agent1 is the only non-punisher (seer who didn't punish).
    #   meta-seers = the OTHER agents (agent0, agent2):
    #     agent0 meta-see-roll = 0.9 (>=S -> does not see).
    #     agent2 meta-see-roll = 0.1 (<S -> sees); meta-punish-roll = 0.1 (<v=1 ->
    #       meta-punishes): agent1 -E', agent2 -P'.
    # Then S1=0.9, S2=0.9 (no further defections from the meek agents).
    m.rng = ScriptedRandom([0.5, 0.1, 0.9, 0.9, 0.9, 0.1, 0.1, 0.9, 0.9])
    m.play_round()
    a0, a1, a2 = m.agent_list
    assert a0.payoff == pytest.approx(m.T)                    # defector: +T, never seen/punished
    assert a1.payoff == pytest.approx(-m.H - m.E_meta)        # hurt + meta-punished
    assert a2.payoff == pytest.approx(-m.H - m.P_meta)        # hurt + paid meta-cost


def test_metanorm_flag_changes_only_the_meta_step():
    # With the SAME scripted draws, the no-metanorm arm produces the norms-game payoffs
    # WITHOUT the meta-punishment; the metanorm arm differs ONLY by the agent1/agent2
    # meta-punishment terms. Everything up to (and including) the defection + ordinary
    # punishment is identical.
    draws = [0.5, 0.1, 0.9, 0.9, 0.9, 0.1, 0.1, 0.9, 0.9]

    no_meta = NormsModel(n=3, metanorms=False, rounds_per_gen=1, mut_rate=0.0,
                         n_generations=0, seed=0)
    meta = NormsModel(n=3, metanorms=True, rounds_per_gen=1, mut_rate=0.0,
                      n_generations=0, seed=0)
    for m in (no_meta, meta):
        for a in m.agent_list:
            a.payoff = 0.0
        m.agent_list[0].B, m.agent_list[0].V = 7, 0
        m.agent_list[1].B, m.agent_list[1].V = 0, 0
        m.agent_list[2].B, m.agent_list[2].V = 0, 7
        m.rng = ScriptedRandom(list(draws))
        m.play_round()

    # agent0 (the defector) and the hurt term are identical in both arms.
    assert no_meta.agent_list[0].payoff == pytest.approx(meta.agent_list[0].payoff)
    # In the no-metanorm arm, agents 1 and 2 are ONLY hurt (no meta-punishment):
    assert no_meta.agent_list[1].payoff == pytest.approx(-no_meta.H)
    assert no_meta.agent_list[2].payoff == pytest.approx(-no_meta.H)
    # The metanorm arm adds EXACTLY the meta terms on top:
    assert meta.agent_list[1].payoff == pytest.approx(no_meta.agent_list[1].payoff - meta.E_meta)
    assert meta.agent_list[2].payoff == pytest.approx(no_meta.agent_list[2].payoff - meta.P_meta)


# -- Axelrod's selection + gene-bounded mutation ------------------------------

def test_selection_above_mean_reproduces_below_mean_dies():
    # Hand-set payoffs so the spread is wide: one clear winner, one clear loser, one
    # middling. With mut_rate=0 the next generation's genes come purely from the
    # survivors' genotypes. The loser's distinctive genotype must NOT appear; the
    # winner's genotype (reproducing twice) must appear at least once.
    m = NormsModel(n=3, metanorms=False, rounds_per_gen=1, mut_rate=0.0,
                   n_generations=0, seed=0)
    win, mid, lose = m.agent_list
    win.B, win.V = 7, 7
    mid.B, mid.V = 3, 3
    lose.B, lose.V = 0, 0
    win.payoff, mid.payoff, lose.payoff = 100.0, 0.0, -100.0   # mean 0, large std
    m.reproduce()
    genes = {(a.B, a.V) for a in m.agent_list}
    assert (7, 7) in genes              # winner survived
    assert (0, 0) not in genes          # loser died out


def test_mutation_keeps_genes_in_range():
    # With a high mutation rate over many generations, every gene must always stay in
    # {0..7} (3-bit flips can never leave the range).
    m = NormsModel(n=20, metanorms=False, rounds_per_gen=2, mut_rate=0.5,
                   n_generations=30, seed=1)
    m.run()
    for a in m.agent_list:
        assert 0 <= a.B <= GENE_MAX and 0 <= a.V <= GENE_MAX


def test_mutate_gene_only_flips_within_three_bits():
    m = NormsModel(n=2, mut_rate=1.0, seed=0)   # every bit flips
    # mut_rate=1 flips all 3 bits: value -> value XOR 0b111 == 7 - value.
    for v in range(GENE_MAX + 1):
        assert m._mutate_gene(v) == GENE_MAX - v
    m0 = NormsModel(n=2, mut_rate=0.0, seed=0)  # no bit flips -> identity
    for v in range(GENE_MAX + 1):
        assert m0._mutate_gene(v) == v


def test_population_size_preserved_each_generation():
    m = NormsModel(n=20, metanorms=True, rounds_per_gen=3, mut_rate=0.02,
                   n_generations=10, seed=2)
    m.run()
    assert len(m.agent_list) == 20


# -- determinism + arm equivalence --------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(metanorms=True, seed=42, n_generations=40, measure_last=10)
    b = run_single(metanorms=True, seed=42, n_generations=40, measure_last=10)
    assert a["mean_V_series"] == b["mean_V_series"]
    assert a["mean_B_series"] == b["mean_B_series"]
    assert a["window_mean_V"] == b["window_mean_V"]


def test_arms_share_initial_population():
    # The two arms differ ONLY in the metanorm step; with the same seed they start from
    # the identical initial gene draw (generation-0 baseline mean B and V match).
    no_meta = run_single(metanorms=False, seed=7, n_generations=0)
    meta = run_single(metanorms=True, seed=7, n_generations=0)
    assert no_meta["mean_B_series"][0] == pytest.approx(meta["mean_B_series"][0])
    assert no_meta["mean_V_series"][0] == pytest.approx(meta["mean_V_series"][0])


def test_different_seed_can_differ_but_stays_in_range():
    a = run_single(metanorms=True, seed=1, n_generations=30)
    b = run_single(metanorms=True, seed=2, n_generations=30)
    for res in (a, b):
        assert all(0.0 <= x <= GENE_MAX for x in res["mean_V_series"])
        assert all(0.0 <= x <= GENE_MAX for x in res["mean_B_series"])


# -- run summary + estimator --------------------------------------------------

def test_run_summary_shape():
    res = run_single(metanorms=False, seed=0, n_generations=30, measure_last=10)
    assert res["n"] == 20 and res["metanorms"] is False
    assert len(res["mean_V_series"]) == 31         # gen-0 baseline + 30 generations
    assert len(res["mean_B_series"]) == 31
    assert 0.0 <= res["window_mean_V"] <= GENE_MAX
    assert 0.0 <= res["window_mean_B"] <= GENE_MAX


def test_tail_mean_is_trailing_window_mean():
    series = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert tail_mean(series, window=2) == pytest.approx(4.5)    # mean(4, 5)
    assert tail_mean(series, window=100) == pytest.approx(3.0)  # whole series
    assert tail_mean([], window=5) == 0.0


def test_run_many_seeds_shape():
    out = run_many_seeds(metanorms=False, n_seeds=4, n_generations=20, measure_last=5)
    assert out["n_seeds"] == 4
    assert len(out["per_seed_window_V"]) == 4
    assert len(out["per_seed_window_B"]) == 4
    assert out["min_window_V"] <= out["mean_window_V"] <= out["max_window_V"]
