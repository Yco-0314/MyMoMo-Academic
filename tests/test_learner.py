"""Tests for FeedforwardLearner — the library learned-operator (ADR-013 W2 fix).

Proves the math is correct so generated agent code trusting the library is
safe: training reduces loss, the learner recovers a learnable mapping,
embeddings are trainable, and the nearest-neighbour helper works.
"""
from __future__ import annotations

import numpy as np

from abm_auto.runtime import FeedforwardLearner
from abm_auto.runtime._learner import self_test


def _copy_pairs(n: int) -> list[tuple[int, int]]:
    return [(i, (i + 1) % n) for i in range(n)]


def test_self_test_passes() -> None:
    assert self_test() is True


def test_exported_from_runtime() -> None:
    # generated code does `from abm_auto.runtime import FeedforwardLearner`
    from abm_auto import runtime
    assert hasattr(runtime, "FeedforwardLearner")


def test_predict_shape_and_range() -> None:
    L = FeedforwardLearner(n_items=5, embed_dim=4, hidden_dim=4, seed=0)
    y = L.predict(2)
    assert isinstance(y, int)
    assert 0 <= y < 5
    proba = L.predict_proba(2)
    assert proba.shape == (5,)
    assert abs(float(proba.sum()) - 1.0) < 1e-9   # softmax normalised


def test_training_reduces_loss_and_recovers_mapping() -> None:
    n = 8
    L = FeedforwardLearner(n_items=n, embed_dim=8, hidden_dim=8,
                           learning_rate=0.2, seed=0)
    pairs = _copy_pairs(n)
    loss0 = L.train(pairs, epochs=1)
    for _ in range(400):
        L.train(pairs, epochs=1)
    loss1 = L.train(pairs, epochs=1)
    assert loss1 < loss0 * 0.5
    recovered = sum(L.predict(i) == (i + 1) % n for i in range(n))
    assert recovered == n


def test_embeddings_are_trainable() -> None:
    """Training must change the embedding matrix (joint update with weights)."""
    L = FeedforwardLearner(n_items=6, embed_dim=4, hidden_dim=4,
                           learning_rate=0.2, seed=0)
    before = L.E.copy()
    L.train(_copy_pairs(6), epochs=20)
    assert not np.allclose(before, L.E)


def test_train_empty_is_noop() -> None:
    L = FeedforwardLearner(n_items=4, seed=0)
    before = L.E.copy()
    assert L.train([]) == 0.0
    assert np.allclose(before, L.E)


def test_nearest_excludes_self() -> None:
    L = FeedforwardLearner(n_items=6, embed_dim=4, seed=0)
    nn = L.nearest(0)
    assert nn != 0
    assert 0 <= nn < 6


def test_deterministic_given_seed() -> None:
    a = FeedforwardLearner(n_items=5, seed=7)
    b = FeedforwardLearner(n_items=5, seed=7)
    pairs = _copy_pairs(5)
    assert a.train(pairs, epochs=10) == b.train(pairs, epochs=10)


def test_rejects_degenerate_vocab() -> None:
    import pytest
    with pytest.raises(ValueError):
        FeedforwardLearner(n_items=1)
