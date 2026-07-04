"""q-voter nonlinear opinion dynamics on a complete graph.

Source family: Castellano, Munoz & Pastor-Satorras (2009), nonlinear q-voter
dynamics. This module implements the well-mixed q-panel rule used by the Batch 7
locked reproduction: binary agents, asynchronous target updates, q neighbours sampled
with replacement from the complete graph, unanimous panels persuade, split panels only
act through epsilon noise.

Rules:
  * N persistent binary opinions in {0, 1}.
  * One update picks a target uniformly at random.
  * q neighbours are sampled with replacement from all other agents.
  * If the q-neighbour panel is unanimous, the target adopts that opinion.
  * If the panel is split, the target flips with probability epsilon.
  * q=1 and epsilon=0 reduces to the ordinary linear voter copy rule.
  * Run until all-0/all-1 consensus or a fixed sweep cap.

The implementation is intentionally small and deterministic. A single seeded
``random.Random`` chain drives target choice, panel sampling, and epsilon flips.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


class QVoterModel:
    """Complete-graph q-voter process with asynchronous model-driven updates."""

    def __init__(
        self,
        *,
        n: int = 400,
        u: float = 0.5,
        q: int = 4,
        epsilon: float = 0.0,
        seed: int = 0,
        max_sweeps: Optional[int] = None,
    ) -> None:
        if n < 2:
            raise ValueError(f"n must be >= 2; got {n}")
        if not (0.0 <= u <= 1.0):
            raise ValueError(f"u must be in [0, 1]; got {u}")
        if q < 1:
            raise ValueError(f"q must be >= 1; got {q}")
        if not (0.0 <= epsilon <= 1.0):
            raise ValueError(f"epsilon must be in [0, 1]; got {epsilon}")
        if max_sweeps is not None and max_sweeps < 1:
            raise ValueError(f"max_sweeps must be >= 1 when provided; got {max_sweeps}")

        self.n = n
        self.u = u
        self.q = q
        self.epsilon = epsilon
        self.seed = seed
        self.max_sweeps = max_sweeps if max_sweeps is not None else 200 * n
        self.rng = random.Random(seed)

        self.n_up0 = int(round(u * n))
        self.opinions: List[int] = [1 if i < self.n_up0 else 0 for i in range(n)]
        self._up = self.n_up0

    def up_count(self) -> int:
        return self._up

    def up_fraction(self) -> float:
        return self._up / self.n

    def magnetization(self) -> float:
        return (2 * self._up - self.n) / self.n

    def at_consensus(self) -> bool:
        return self._up == 0 or self._up == self.n

    def _set_opinion(self, target: int, opinion: int) -> None:
        before = self.opinions[target]
        if before == opinion:
            return
        self.opinions[target] = opinion
        self._up += 1 if opinion == 1 else -1

    def apply_panel(self, *, target: int, panel: List[int]) -> None:
        """Apply one q-panel to a target.

        ``panel`` contains neighbour indices, not opinions. Sampling with replacement
        means duplicate neighbour ids are valid; the target itself is not.
        """
        if not (0 <= target < self.n):
            raise ValueError(f"target out of range: {target}")
        if len(panel) != self.q:
            raise ValueError(f"panel length must equal q={self.q}; got {len(panel)}")
        if any((idx < 0 or idx >= self.n) for idx in panel):
            raise ValueError("panel contains an out-of-range neighbour")
        if any(idx == target for idx in panel):
            raise ValueError("panel cannot contain the target")

        panel_opinions = [self.opinions[idx] for idx in panel]
        first = panel_opinions[0]
        if all(op == first for op in panel_opinions):
            self._set_opinion(target, first)
            return
        if self.rng.random() < self.epsilon:
            self._set_opinion(target, 1 - self.opinions[target])

    def sample_panel(self, *, target: int) -> List[int]:
        """Sample q neighbour ids with replacement, excluding ``target`` in O(q)."""
        if not (0 <= target < self.n):
            raise ValueError(f"target out of range: {target}")
        panel: List[int] = []
        for _ in range(self.q):
            draw = self.rng.randrange(self.n - 1)
            panel.append(draw if draw < target else draw + 1)
        return panel

    def update(self) -> None:
        target = self.rng.randrange(self.n)
        self.apply_panel(target=target, panel=self.sample_panel(target=target))

    def run(self) -> Dict[str, Any]:
        total_updates = 0
        reached = self.at_consensus()
        max_updates = self.max_sweeps * self.n
        while not reached and total_updates < max_updates:
            self.update()
            total_updates += 1
            reached = self.at_consensus()

        consensus = None
        if self._up == self.n:
            consensus = 1
        elif self._up == 0:
            consensus = 0

        return {
            "n": self.n,
            "u": self.u,
            "q": self.q,
            "epsilon": self.epsilon,
            "seed": self.seed,
            "n_up0": self.n_up0,
            "reached_consensus": reached,
            "consensus": consensus,
            "all_up": consensus == 1,
            "final_up": self._up,
            "final_up_fraction": self.up_fraction(),
            "final_magnetization": self.magnetization(),
            "total_updates": total_updates,
            "sweeps": total_updates / self.n,
            "max_sweeps": self.max_sweeps,
            "capped": not reached,
        }


def run_single(
    *,
    n: int = 400,
    u: float = 0.5,
    q: int = 4,
    epsilon: float = 0.0,
    seed: int = 0,
    max_sweeps: Optional[int] = None,
) -> Dict[str, Any]:
    return QVoterModel(
        n=n,
        u=u,
        q=q,
        epsilon=epsilon,
        seed=seed,
        max_sweeps=max_sweeps,
    ).run()


def run_many_seeds(
    *,
    n: int = 400,
    u: float = 0.5,
    q: int = 4,
    epsilon: float = 0.0,
    n_runs: int = 100,
    seed_base: int = 0,
    max_sweeps: Optional[int] = None,
) -> Dict[str, Any]:
    if n_runs < 1:
        raise ValueError(f"n_runs must be >= 1; got {n_runs}")
    effective_max_sweeps = max_sweeps if max_sweeps is not None else 200 * n

    per_run: List[Dict[str, Any]] = []
    n_all_up = 0
    n_consensus = 0
    n_capped = 0
    mags: List[float] = []

    for i in range(n_runs):
        seed = seed_base + i
        result = run_single(
            n=n,
            u=u,
            q=q,
            epsilon=epsilon,
            seed=seed,
            max_sweeps=effective_max_sweeps,
        )
        if result["all_up"]:
            n_all_up += 1
        if result["reached_consensus"]:
            n_consensus += 1
        if result["capped"]:
            n_capped += 1
        mags.append(result["final_magnetization"])
        per_run.append({
            "seed": seed,
            "consensus": result["consensus"],
            "all_up": result["all_up"],
            "final_up": result["final_up"],
            "final_magnetization": result["final_magnetization"],
            "sweeps": result["sweeps"],
            "capped": result["capped"],
        })

    p_all_up = n_all_up / n_runs
    consensus_rate = n_consensus / n_runs
    capped_rate = n_capped / n_runs
    mean_mag = sum(mags) / len(mags)
    se_p = (p_all_up * (1.0 - p_all_up) / n_runs) ** 0.5

    return {
        "n": n,
        "u": u,
        "q": q,
        "epsilon": epsilon,
        "n_runs": n_runs,
        "seed_base": seed_base,
        "max_sweeps": effective_max_sweeps,
        "n_all_up": n_all_up,
        "p_all_up": p_all_up,
        "se_p_all_up": se_p,
        "n_consensus": n_consensus,
        "consensus_rate": consensus_rate,
        "n_capped": n_capped,
        "capped_rate": capped_rate,
        "mean_final_magnetization": mean_mag,
        "expected_linear_magnetization": 2 * u - 1,
        "per_run": per_run,
    }
