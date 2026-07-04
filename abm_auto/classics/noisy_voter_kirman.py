"""Noisy voter / Kirman binary herding model on a complete graph.

The process augments the absorbing complete-graph voter model with spontaneous state
changes. One target is selected per update. With probability ``a`` it flips independent
of neighbours; otherwise it copies one randomly selected other agent. The spontaneous
component removes the all-0/all-1 absorbing states and yields an ergodic stationary
magnetization distribution.

The module is intentionally small and deterministic: a single seeded RNG chain drives
target choice, source choice, and spontaneous-vs-copy branching.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional


class NoisyVoterModel:
    """Complete-graph noisy voter / Kirman process."""

    def __init__(self, *, n: int = 400, u: float = 0.5, a: float = 0.01,
                 seed: int = 0) -> None:
        if n < 2:
            raise ValueError(f"n must be >= 2; got {n}")
        if not (0.0 <= u <= 1.0):
            raise ValueError(f"u must be in [0, 1]; got {u}")
        if not (0.0 <= a <= 1.0):
            raise ValueError(f"a must be in [0, 1]; got {a}")
        self.n = n
        self.u = u
        self.a = a
        self.seed = seed
        self.rng = random.Random(seed)

        self.n_up0 = int(round(u * n))
        self.opinions: List[int] = [1 if i < self.n_up0 else 0 for i in range(n)]
        self._up = self.n_up0
        self.total_updates = 0

    def up_count(self) -> int:
        return self._up

    def magnetization(self) -> float:
        return (2 * self._up - self.n) / self.n

    def _set_opinion(self, target: int, opinion: int) -> None:
        before = self.opinions[target]
        if before == opinion:
            return
        self.opinions[target] = opinion
        self._up += 1 if opinion == 1 else -1

    def sample_source(self, *, target: int) -> int:
        if not (0 <= target < self.n):
            raise ValueError(f"target out of range: {target}")
        draw = self.rng.randrange(self.n - 1)
        return draw if draw < target else draw + 1

    def apply_update(self, *, target: int, source: Optional[int], spontaneous: bool) -> None:
        if not (0 <= target < self.n):
            raise ValueError(f"target out of range: {target}")
        if spontaneous:
            self._set_opinion(target, 1 - self.opinions[target])
            return
        if source is None:
            raise ValueError("source is required for a copy update")
        if not (0 <= source < self.n):
            raise ValueError(f"source out of range: {source}")
        if source == target:
            raise ValueError("source cannot equal target")
        self._set_opinion(target, self.opinions[source])

    def update(self) -> None:
        target = self.rng.randrange(self.n)
        spontaneous = self.rng.random() < self.a
        source = None if spontaneous else self.sample_source(target=target)
        self.apply_update(target=target, source=source, spontaneous=spontaneous)
        self.total_updates += 1

    def run_trace(self, *, burn_in: int, samples: int, record_every: int) -> Dict[str, Any]:
        if burn_in < 0:
            raise ValueError(f"burn_in must be >= 0; got {burn_in}")
        if samples < 1:
            raise ValueError(f"samples must be >= 1; got {samples}")
        if record_every < 1:
            raise ValueError(f"record_every must be >= 1; got {record_every}")

        for _ in range(burn_in):
            self.update()

        trace: List[float] = []
        for _ in range(samples):
            for _ in range(record_every):
                self.update()
            trace.append(self.magnetization())

        stats = edge_center_mass(trace)
        mean = sum(trace) / len(trace)
        var = sum((x - mean) ** 2 for x in trace) / len(trace)
        return {
            "n": self.n,
            "u": self.u,
            "a": self.a,
            "a_times_n": self.a * self.n,
            "seed": self.seed,
            "burn_in": burn_in,
            "samples": samples,
            "record_every": record_every,
            "total_updates": self.total_updates,
            "magnetization_trace": trace,
            "mean_magnetization": mean,
            "magnetization_std": var ** 0.5,
            "edge_mass": stats["edge_mass"],
            "center_mass": stats["center_mass"],
            "edge_center_ratio": stats["edge_center_ratio"],
        }


def edge_center_mass(
    trace: List[float],
    *,
    edge_threshold: float = 0.6,
    center_threshold: float = 0.2,
) -> Dict[str, float]:
    if not trace:
        raise ValueError("trace must be non-empty")
    if not (0.0 <= center_threshold < edge_threshold <= 1.0):
        raise ValueError("thresholds must satisfy 0 <= center < edge <= 1")
    n = len(trace)
    edge = sum(1 for m in trace if abs(m) > edge_threshold) / n
    center = sum(1 for m in trace if abs(m) < center_threshold) / n
    ratio = math.inf if center == 0.0 else edge / center
    return {
        "edge_mass": edge,
        "center_mass": center,
        "edge_center_ratio": ratio,
    }


def run_stationary(
    *,
    n: int = 400,
    u: float = 0.5,
    a: float = 0.01,
    seed: int = 0,
    burn_in: int = 20_000,
    samples: int = 800,
    record_every: int = 20,
) -> Dict[str, Any]:
    return NoisyVoterModel(n=n, u=u, a=a, seed=seed).run_trace(
        burn_in=burn_in,
        samples=samples,
        record_every=record_every,
    )
