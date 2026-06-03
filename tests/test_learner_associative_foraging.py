"""Second adapter for FeedforwardLearner — cross-domain, "two adapters = seam".

The first FeedforwardLearner adapter is the Yaman semantic model (predict the
item that completes a recipe). This is a different DOMAIN: associative
cue→reward learning, the kind of model in behavioural-ecology / animal-learning
ABMs. A population of foragers each learns, from sampled EXPERIENCE, which
environmental cue predicts which reward location (a fixed but unknown
permutation). The same operator recovers the environment's structure.

Different from Yaman: a foraging/animal-cognition framing (not cultural
semantics), the learner predicts a location not a co-ingredient, and learning
is from per-agent foraging experience. Same operator. If a population of
independent agents recovers the cue→reward map here, the learner is a real
reusable seam — not bespoke to Yaman.
"""
from __future__ import annotations

import random

from abm_auto.runtime import FeedforwardLearner

N_CUES = 8


def _reward_map() -> dict:
    # a fixed permutation: cue i -> reward location (i*3 + 1) mod 8 (a bijection)
    return {i: (i * 3 + 1) % N_CUES for i in range(N_CUES)}


def _accuracy(learner: FeedforwardLearner, rmap: dict) -> float:
    correct = sum(learner.predict(c) == rmap[c] for c in range(N_CUES))
    return correct / N_CUES


def _run_foraging(seed: int, rounds: int):
    """N foragers, each learning the cue→reward map from its own experience.
    Each round every agent visits 2 random cues, records (cue, reward), and
    retrains its learner on accumulated experience (the same experience-replay
    shape as Yaman's updateModels). Returns mean population accuracy."""
    rmap = _reward_map()
    rng = random.Random(seed)
    n_agents = 12
    agents = [{"learner": FeedforwardLearner(n_items=N_CUES, embed_dim=8,
                                             hidden_dim=8, learning_rate=0.2,
                                             seed=seed * 100 + a),
               "memory": []}
              for a in range(n_agents)]

    for _ in range(rounds):
        for ag in agents:
            for _ in range(2):                       # forage 2 cues this round
                c = rng.randint(0, N_CUES - 1)
                ag["memory"].append((c, rmap[c]))
            ag["learner"].train(ag["memory"], epochs=5)

    return sum(_accuracy(ag["learner"], rmap) for ag in agents) / n_agents


def test_population_learns_cue_reward_map() -> None:
    """A population of independent foragers recovers the environment's hidden
    cue→reward permutation from experience — the SAME operator, a new domain."""
    acc = _run_foraging(seed=0, rounds=60)
    assert acc > 0.85, f"population accuracy {acc:.2f} — failed to learn the map"


def test_naive_learner_is_at_chance() -> None:
    """An untrained learner predicts at chance (1/8) — the learning, not the
    operator's init, is what recovers the map (rules out a trivial pass)."""
    rmap = _reward_map()
    naive = FeedforwardLearner(n_items=N_CUES, embed_dim=8, hidden_dim=8, seed=0)
    # average chance accuracy across several fresh learners
    accs = [
        _accuracy(FeedforwardLearner(n_items=N_CUES, embed_dim=8, hidden_dim=8, seed=s), rmap)
        for s in range(20)
    ]
    assert sum(accs) / len(accs) < 0.35           # near chance, far below the learned 0.85+


def test_learning_is_reproducible() -> None:
    assert _run_foraging(seed=3, rounds=60) == _run_foraging(seed=3, rounds=60)
