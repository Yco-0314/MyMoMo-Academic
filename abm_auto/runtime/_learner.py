"""ABM Auto Runtime — FeedforwardLearner, a library learned-operator.

The runtime answer to the W2 codegen wall found in the Yaman reproduction
(ADR-013 Path 1): an agent that *learns a representation* could not be
generated, because the LLM had to write the training loop itself and got
it wrong (the trainable semantic net silently degraded to a success
probability).

The fix mirrors how topology and calibration already work: the operator
is LIBRARY CODE (written once, self-tested once, always correct), and
generated agent code only *uses* it — never reimplements it. Just as
generated models call ``topologies.watts_strogatz(...)`` and calibration
calls ``fit(...)``, a learned-representation agent calls
``FeedforwardLearner(...).train(...)`` / ``.predict(...)``. The LLM never
touches forward-pass / cross-entropy / backprop.

Scope (minimal, per the design grilling): a single-hidden-layer
feedforward classifier over a fixed item vocabulary, with TRAINABLE item
embeddings as the input representation — exactly the
"entity-embedding + small MLP" pattern (word2vec / recommender /
Yaman's distributional semantic model). Pure numpy, hand-written
backprop (no torch dependency in the runtime). The classifier and the
embeddings are trained jointly.

What is library (here) vs strategy (LLM-written): the *trainable*
parts — embeddings + MLP + the joint training loop — are here. How an
agent *uses* the learned representation (e.g. nearest-neighbour
generalization) is agent strategy; ``nearest`` is offered as a read-only
helper the agent may call, but choosing to call it is the agent's logic.
"""
from __future__ import annotations

from typing import Optional

import numpy as np


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


class FeedforwardLearner:
    """Trainable item→item predictor with learned item embeddings.

    Predicts, for an input item x (an index into a fixed vocabulary of
    ``n_items``), a distribution over the item y that completes a
    successful pairing — p(y | x). The input representation is a learned
    embedding (``embed_dim``); a single hidden layer (``hidden_dim``,
    ReLU) maps it to a softmax over the vocabulary.

    Library-grade, deterministic given ``seed``. Trained by cross-entropy
    + hand-written backprop; embeddings and weights update jointly.

    Generated agent code uses only: ``predict``, ``train``, ``nearest``,
    and (rarely) ``embedding_of``. It never implements the math.
    """

    def __init__(
        self,
        n_items: int,
        embed_dim: int = 16,
        hidden_dim: int = 16,
        learning_rate: float = 0.001,
        seed: int = 0,
    ) -> None:
        if n_items < 2:
            raise ValueError(f"n_items must be >= 2, got {n_items}")
        self.n_items = int(n_items)
        self.embed_dim = int(embed_dim)
        self.hidden_dim = int(hidden_dim)
        self.lr = float(learning_rate)
        rng = np.random.default_rng(seed)
        # He-ish init scaled small for stability under hand-written SGD.
        self.E = rng.normal(0, 0.1, (self.n_items, self.embed_dim))      # item embeddings
        self.W1 = rng.normal(0, 0.1, (self.embed_dim, self.hidden_dim))  # embed → hidden
        self.b1 = np.zeros(self.hidden_dim)
        self.W2 = rng.normal(0, 0.1, (self.hidden_dim, self.n_items))    # hidden → vocab
        self.b2 = np.zeros(self.n_items)

    # ── forward ──────────────────────────────────────────────────────────

    def _forward(self, x_idx: np.ndarray):
        """Forward pass for a batch of input item indices. Returns
        (probs, cache) where cache holds activations for backprop."""
        emb = self.E[x_idx]                       # (B, embed_dim)
        h_pre = emb @ self.W1 + self.b1           # (B, hidden_dim)
        h = np.maximum(0.0, h_pre)                # ReLU
        logits = h @ self.W2 + self.b2            # (B, n_items)
        probs = _softmax(logits)                  # (B, n_items)
        return probs, (x_idx, emb, h_pre, h)

    def predict(self, item: int, *, argmax: bool = True, seed: int = 0) -> int:
        """Predict the complementary item for ``item``. argmax by default;
        set argmax=False to sample from the predicted distribution."""
        probs, _ = self._forward(np.array([item]))
        p = probs[0]
        if argmax:
            return int(p.argmax())
        rng = np.random.default_rng(seed)
        return int(rng.choice(self.n_items, p=p))

    def predict_proba(self, item: int) -> np.ndarray:
        """Full predicted distribution p(y | item)."""
        probs, _ = self._forward(np.array([item]))
        return probs[0]

    # ── train ────────────────────────────────────────────────────────────

    def train(self, pairs: list[tuple[int, int]], epochs: int = 1) -> float:
        """One (or more) epochs of cross-entropy SGD over (input, target)
        item-index pairs. Updates embeddings + both layers jointly.
        Returns the mean cross-entropy loss of the final epoch. No-op
        (returns 0.0) on empty input."""
        if not pairs:
            return 0.0
        x_idx = np.array([a for a, _ in pairs])
        y_idx = np.array([b for _, b in pairs])
        B = len(pairs)
        last_loss = 0.0
        for _ in range(max(1, epochs)):
            probs, (xi, emb, h_pre, h) = self._forward(x_idx)
            # cross-entropy loss
            eps = 1e-12
            last_loss = float(-np.log(probs[np.arange(B), y_idx] + eps).mean())
            # backprop
            dlogits = probs.copy()
            dlogits[np.arange(B), y_idx] -= 1.0
            dlogits /= B                                  # (B, n_items)
            dW2 = h.T @ dlogits                           # (hidden, n_items)
            db2 = dlogits.sum(axis=0)
            dh = dlogits @ self.W2.T                      # (B, hidden)
            dh_pre = dh * (h_pre > 0)                     # ReLU grad
            dW1 = emb.T @ dh_pre                          # (embed, hidden)
            db1 = dh_pre.sum(axis=0)
            demb = dh_pre @ self.W1.T                     # (B, embed)
            # SGD step
            self.W2 -= self.lr * dW2
            self.b2 -= self.lr * db2
            self.W1 -= self.lr * dW1
            self.b1 -= self.lr * db1
            # scatter-add embedding grads back to E (inputs may repeat)
            np.add.at(self.E, xi, -self.lr * demb)
        return last_loss

    # ── embedding-space helpers (agent strategy MAY call these) ──────────

    def embedding_of(self, item: int) -> np.ndarray:
        return self.E[item].copy()

    def nearest(self, item: int, *, exclude_self: bool = True) -> int:
        """Item whose embedding is nearest (Euclidean) to ``item``'s. A
        read-only helper for strategies like Yaman's generalization;
        calling it is the agent's choice, not the operator's behaviour."""
        d = np.linalg.norm(self.E - self.E[item], axis=1)
        if exclude_self:
            d[item] = np.inf
        return int(d.argmin())


def self_test() -> bool:
    """Library self-test (ADR-013 Gate philosophy applied to the operator):
    on a synthetic learnable mapping, training must reduce loss and the
    learner must recover the mapping. Proves the forward/backprop math is
    correct — checked once so generated code trusting the library is safe.

    Task: a fixed deterministic complement map (item i pairs with
    (i+1) mod n). After training, argmax-predict must recover it for a
    clear majority of items, and loss must drop.
    """
    # lr=0.2 / ~400 epochs converges this task to loss≈0.01, 8/8 recovery
    # (verified by an lr×epoch sweep: the math is correct; lr=0.05/400ep
    # merely under-trains). Use a setting comfortably inside the
    # converging regime so the self-test is a sound math check, not a
    # convergence-speed gamble.
    n = 8
    learner = FeedforwardLearner(n_items=n, embed_dim=8, hidden_dim=8,
                                 learning_rate=0.2, seed=0)
    pairs = [(i, (i + 1) % n) for i in range(n)]
    loss0 = learner.train(pairs, epochs=1)
    for _ in range(400):
        learner.train(pairs, epochs=1)
    loss1 = learner.train(pairs, epochs=1)
    if not (loss1 < loss0 * 0.5):
        return False                              # training must clearly reduce loss
    correct = sum(learner.predict(i) == (i + 1) % n for i in range(n))
    return correct == n                           # recovers the full mapping
