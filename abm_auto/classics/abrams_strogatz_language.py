"""Abrams-Strogatz two-language competition model.

This module implements the well-mixed stochastic form used by the Batch 7 locked
study. Agents speak language A (1) or B (0). At each update one speaker is selected.
A B speaker switches to A with probability ``s_A * x_A**alpha``; an A speaker switches
to B with probability ``(1 - s_A) * x_B**alpha``. For ``alpha > 1`` the two-language
mean-field model has stable monolingual endpoints and an unstable interior boundary.

The implementation is deliberately small and deterministic: a single seeded RNG chain
drives speaker selection and transition draws.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


def basin_boundary(*, status_a: float, alpha: float) -> float:
    """Mean-field unstable fixed point for the two-language model."""
    if not (0.0 < status_a < 1.0):
        raise ValueError(f"status_a must be in (0, 1); got {status_a}")
    if alpha <= 1.0:
        raise ValueError(f"alpha must be > 1; got {alpha}")
    r = ((1.0 - status_a) / status_a) ** (1.0 / (alpha - 1.0))
    return r / (1.0 + r)


def classify_outcome(x: float, *, low: float = 0.05, high: float = 0.95) -> str:
    if not (0.0 <= x <= 1.0):
        raise ValueError(f"x must be in [0, 1]; got {x}")
    if not (0.0 <= low < high <= 1.0):
        raise ValueError("thresholds must satisfy 0 <= low < high <= 1")
    if x >= high:
        return "A"
    if x <= low:
        return "B"
    return "interior"


def measured_boundary(rows: List[Dict[str, Any]]) -> Optional[float]:
    """Linear crossing estimate where P(A wins) crosses 0.5 across initial shares."""
    if not rows:
        return None
    ordered = sorted(rows, key=lambda r: r["initial_a"])
    for row in ordered:
        if row["p_a_win"] == 0.5:
            return row["initial_a"]
    for left, right in zip(ordered, ordered[1:]):
        x0, y0 = left["initial_a"], left["p_a_win"]
        x1, y1 = right["initial_a"], right["p_a_win"]
        if (y0 - 0.5) * (y1 - 0.5) <= 0.0 and y0 != y1:
            return x0 + (0.5 - y0) * (x1 - x0) / (y1 - y0)
    return None


class AbramsStrogatzModel:
    """Well-mixed stochastic Abrams-Strogatz language competition."""

    def __init__(
        self,
        *,
        n: int = 500,
        initial_a: float = 0.5,
        status_a: float = 0.6,
        alpha: float = 1.31,
        seed: int = 0,
        max_sweeps: int = 2000,
    ) -> None:
        if n < 2:
            raise ValueError(f"n must be >= 2; got {n}")
        if not (0.0 <= initial_a <= 1.0):
            raise ValueError(f"initial_a must be in [0, 1]; got {initial_a}")
        if not (0.0 < status_a < 1.0):
            raise ValueError(f"status_a must be in (0, 1); got {status_a}")
        if alpha <= 1.0:
            raise ValueError(f"alpha must be > 1; got {alpha}")
        if max_sweeps < 1:
            raise ValueError(f"max_sweeps must be >= 1; got {max_sweeps}")
        self.n = n
        self.initial_a = initial_a
        self.status_a = status_a
        self.alpha = alpha
        self.seed = seed
        self.max_sweeps = max_sweeps
        self.rng = random.Random(seed)

        self.initial_a_count = int(round(initial_a * n))
        self.languages: List[int] = [1 if i < self.initial_a_count else 0 for i in range(n)]
        self._a_count = self.initial_a_count
        self.total_updates = 0

    def a_count(self) -> int:
        return self._a_count

    def a_fraction(self) -> float:
        return self._a_count / self.n

    def switch_probabilities(self) -> tuple[float, float]:
        x_a = self.a_fraction()
        x_b = 1.0 - x_a
        p_to_a = self.status_a * (x_a ** self.alpha)
        p_to_b = (1.0 - self.status_a) * (x_b ** self.alpha)
        return p_to_a, p_to_b

    def _set_language(self, target: int, language: int) -> None:
        before = self.languages[target]
        if before == language:
            return
        self.languages[target] = language
        self._a_count += 1 if language == 1 else -1

    def apply_update(self, *, target: int, draw: float) -> None:
        if not (0 <= target < self.n):
            raise ValueError(f"target out of range: {target}")
        if not (0.0 <= draw <= 1.0):
            raise ValueError(f"draw must be in [0, 1]; got {draw}")
        p_to_a, p_to_b = self.switch_probabilities()
        if self.languages[target] == 0:
            if draw < p_to_a:
                self._set_language(target, 1)
        else:
            if draw < p_to_b:
                self._set_language(target, 0)

    def update(self) -> None:
        target = self.rng.randrange(self.n)
        draw = self.rng.random()
        self.apply_update(target=target, draw=draw)
        self.total_updates += 1

    def run(self) -> Dict[str, Any]:
        max_updates = self.max_sweeps * self.n
        outcome = classify_outcome(self.a_fraction())
        while outcome == "interior" and self.total_updates < max_updates:
            self.update()
            outcome = classify_outcome(self.a_fraction())
        return {
            "n": self.n,
            "initial_a": self.initial_a,
            "initial_a_count": self.initial_a_count,
            "status_a": self.status_a,
            "alpha": self.alpha,
            "seed": self.seed,
            "boundary": basin_boundary(status_a=self.status_a, alpha=self.alpha),
            "final_a": self._a_count,
            "final_a_fraction": self.a_fraction(),
            "outcome": outcome,
            "a_wins": outcome == "A",
            "b_wins": outcome == "B",
            "interior_late": outcome == "interior",
            "sweeps": self.total_updates / self.n,
            "total_updates": self.total_updates,
            "max_sweeps": self.max_sweeps,
            "capped": outcome == "interior",
        }


def run_single(
    *,
    n: int = 500,
    initial_a: float = 0.5,
    status_a: float = 0.6,
    alpha: float = 1.31,
    seed: int = 0,
    max_sweeps: int = 2000,
) -> Dict[str, Any]:
    return AbramsStrogatzModel(
        n=n,
        initial_a=initial_a,
        status_a=status_a,
        alpha=alpha,
        seed=seed,
        max_sweeps=max_sweeps,
    ).run()


def run_many_seeds(
    *,
    n: int = 500,
    initial_a: float = 0.5,
    status_a: float = 0.6,
    alpha: float = 1.31,
    n_runs: int = 80,
    seed_base: int = 0,
    max_sweeps: int = 2000,
) -> Dict[str, Any]:
    if n_runs < 1:
        raise ValueError(f"n_runs must be >= 1; got {n_runs}")

    per_run: List[Dict[str, Any]] = []
    n_a = 0
    n_b = 0
    n_interior = 0
    final_fracs: List[float] = []
    for i in range(n_runs):
        seed = seed_base + i
        result = run_single(
            n=n,
            initial_a=initial_a,
            status_a=status_a,
            alpha=alpha,
            seed=seed,
            max_sweeps=max_sweeps,
        )
        if result["a_wins"]:
            n_a += 1
        if result["b_wins"]:
            n_b += 1
        if result["interior_late"]:
            n_interior += 1
        final_fracs.append(result["final_a_fraction"])
        per_run.append({
            "seed": seed,
            "final_a_fraction": result["final_a_fraction"],
            "outcome": result["outcome"],
            "sweeps": result["sweeps"],
            "capped": result["capped"],
        })

    mean_final = sum(final_fracs) / len(final_fracs)
    return {
        "n": n,
        "initial_a": initial_a,
        "status_a": status_a,
        "alpha": alpha,
        "n_runs": n_runs,
        "seed_base": seed_base,
        "max_sweeps": max_sweeps,
        "boundary": basin_boundary(status_a=status_a, alpha=alpha),
        "n_a_win": n_a,
        "n_b_win": n_b,
        "n_interior": n_interior,
        "p_a_win": n_a / n_runs,
        "p_b_win": n_b / n_runs,
        "p_interior": n_interior / n_runs,
        "mean_final_a_fraction": mean_final,
        "per_run": per_run,
    }
