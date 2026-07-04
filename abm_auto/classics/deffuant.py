"""Deffuant (2000) bounded-confidence opinion dynamics — a faithful agent-based
reproduction.

Source: Deffuant, G., Neau, D., Amblard, F., Weisbuch, G. (2000) "Mixing beliefs
among interacting agents", Advances in Complex Systems 3:87-98.

Rules (verified against the paper):
  * N agents, each holding a continuous opinion ``x`` drawn ~ Uniform[0, 1].
  * The dynamics are PAIRWISE RANDOM ENCOUNTERS (not a synchronous sweep over a
    neighbourhood): one elementary interaction picks a random pair (i, j). If the
    two opinions are close enough — ``|x_i - x_j| < eps`` (the bounded-confidence
    threshold) — they move toward each other:
        x_i += mu * (x_j - x_i)
        x_j += mu * (x_i - x_j)
    with convergence parameter ``mu`` (default 0.5; mu=0.5 means the pair meets in
    the middle). If ``|x_i - x_j| >= eps`` nothing happens (the agents are too far
    apart to influence one another).
  * One "tick" (a SWEEP) is N such random pair interactions, so each tick is on the
    order of one interaction per agent. The model runs until convergence — the
    largest single opinion change observed during a whole sweep drops below a tiny
    tolerance — or a step cap is reached.
  * Outcome = the number of final opinion CLUSTERS: sort the converged opinions and
    count maximal runs whose consecutive gaps are within a small tolerance (0.01).

Locality note (no global oracle): each elementary interaction reads exactly the two
paired agents' own opinions and updates exactly those two. No agent and no update
ever consults a population-level statistic. The platform ``AgentSet`` holds the
agents (the roster + a seeded RNG); the *pairing* is random per interaction, which is
Deffuant's mean-field "fully mixed" encounter model rather than a fixed-network
neighbourhood. Given a seed the whole run is reproducible.

Built on the neutral platform (``abm_auto._platform``): each agent is an
``OpinionAgent`` carrying its scalar opinion; ``DeffuantModel`` drives the random
pairwise interactions over the ``AgentSet`` roster and records (via a
``DataCollector``) the per-sweep max opinion change and the running cluster count.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class OpinionAgent(Agent):
    """One agent carrying a continuous opinion ``x`` in [0, 1].

    The agent is the STATE holder; in Deffuant's encounter dynamics the unit of
    update is a *pair*, not a single agent's autonomous ``step`` (an agent only
    changes when it happens to be drawn into an interaction with a close-enough
    partner). The pairwise update lives on the model (``interact``) so that the
    two-agent locality — read two opinions, write those same two — is explicit.
    """

    def __init__(self, agent_id: int, model: "DeffuantModel", *, opinion: float) -> None:
        super().__init__(agent_id, model)
        self.x = opinion

    def step(self) -> None:  # pragma: no cover - encounter model updates pairs, not agents
        """Deffuant updates pairs drawn by the model, not single agents in roster
        order, so the per-agent ``step`` is intentionally a no-op. The model's
        ``step`` (one sweep of N random pair interactions) is the tick."""
        return None


# -- Model --------------------------------------------------------------------

class DeffuantModel(AgentModel):
    """Drives Deffuant bounded-confidence dynamics to convergence.

    Construct with N, the confidence threshold ``eps``, the convergence rate
    ``mu``, and a seed. ``run`` iterates sweeps (each sweep = N random pair
    interactions) until the largest single opinion change in a whole sweep falls
    below ``move_tol`` (converged) or ``max_sweeps`` is reached, then returns a
    summary dict (final opinions, #clusters, convergence sweeps, per-sweep
    max-move series).
    """

    def __init__(self, n: int = 1000, *, eps: float = 0.2, mu: float = 0.5,
                 seed: int = 0, move_tol: float = 1e-6,
                 cluster_tol: float = 0.01, major_min_size: int = 10,
                 max_sweeps: int = 100_000) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.seed_value = seed
        self.n = n
        self.eps = eps
        self.mu = mu
        self.move_tol = move_tol
        self.cluster_tol = cluster_tol
        self.major_min_size = major_min_size
        self.max_sweeps = max_sweeps

        #: Largest single opinion change in the sweep just committed (convergence
        #: signal + the per-sweep series).
        self._sweep_max_move = float("inf")

        self.agent_list: List[OpinionAgent] = []
        for i in range(n):
            agent = OpinionAgent(i, self, opinion=self.rng.random())  # ~ Uniform[0,1]
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "max_move": lambda m: m._sweep_max_move,
            "clusters": lambda m: m.cluster_count(),
        })

    # -- the elementary Deffuant interaction --
    def interact(self, a: OpinionAgent, b: OpinionAgent) -> float:
        """One bounded-confidence encounter between two agents. If their opinions
        are within ``eps`` they move toward each other by ``mu`` * difference;
        returns the magnitude of the (symmetric) opinion change, else 0.0.

        Reads and writes only ``a.x`` and ``b.x`` — no global state."""
        diff = b.x - a.x
        if abs(diff) >= self.eps:
            return 0.0
        delta = self.mu * diff
        a.x += delta          # a moves toward b
        b.x -= delta          # b moves toward a (symmetric for mu=0.5: they meet)
        return abs(delta)

    def random_pair(self) -> tuple:
        """Draw two DISTINCT agents uniformly at random from the roster."""
        i = self.rng.randrange(self.n)
        j = self.rng.randrange(self.n)
        while j == i:
            j = self.rng.randrange(self.n)
        return self.agent_list[i], self.agent_list[j]

    # -- metrics --
    def opinions(self) -> List[float]:
        return [a.x for a in self.agent_list]

    def cluster_count(self) -> int:
        """Number of final opinion clusters: sort opinions and count maximal runs
        whose consecutive gaps are <= ``cluster_tol``."""
        return count_clusters(self.opinions(), tol=self.cluster_tol)

    # -- tick (one sweep = N random pair interactions) --
    def step(self) -> None:
        """One sweep: N random pairwise interactions. Track the largest single
        opinion change across the sweep (the convergence signal), advance ``t``,
        and record the per-sweep metrics."""
        max_move = 0.0
        for _ in range(self.n):
            a, b = self.random_pair()
            move = self.interact(a, b)
            if move > max_move:
                max_move = move
        self._sweep_max_move = max_move
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate sweeps until convergence (a whole sweep's max move < move_tol)
        or ``max_sweeps``; return the run summary."""
        for _ in range(self.max_sweeps):
            self.step()
            if self._sweep_max_move < self.move_tol:
                break
        final = self.opinions()
        return {
            "n": self.n,
            "eps": self.eps,
            "mu": self.mu,
            "seed": self.seed_value,
            "cluster_tol": self.cluster_tol,
            "major_min_size": self.major_min_size,
            "move_tol": self.move_tol,
            "sweeps": self.t,
            "converged": self._sweep_max_move < self.move_tol,
            "n_clusters": count_clusters(final, tol=self.cluster_tol),
            "n_major_clusters": major_cluster_count(
                final, tol=self.cluster_tol, min_size=self.major_min_size),
            "cluster_sizes": cluster_sizes(final, tol=self.cluster_tol),
            "cluster_centers": cluster_centers(final, tol=self.cluster_tol),
            "final_opinions": final,
            "max_move_series": self.reporter.series("max_move"),
            "cluster_series": self.reporter.series("clusters"),
        }


# -- cluster + analytic helpers -----------------------------------------------

def count_clusters(opinions: Sequence[float], *, tol: float = 0.01) -> int:
    """Count opinion clusters: sort, then split into maximal runs wherever a
    consecutive gap exceeds ``tol``. Empty input → 0."""
    if not opinions:
        return 0
    xs = sorted(opinions)
    clusters = 1
    for prev, cur in zip(xs, xs[1:]):
        if cur - prev > tol:
            clusters += 1
    return clusters


def cluster_sizes(opinions: Sequence[float], *, tol: float = 0.01) -> List[int]:
    """Sizes (agent counts) of each opinion cluster, largest first. Clusters are
    defined as in ``count_clusters`` (sorted runs split at gaps > ``tol``)."""
    if not opinions:
        return []
    xs = sorted(opinions)
    sizes = [1]
    for prev, cur in zip(xs, xs[1:]):
        if cur - prev > tol:
            sizes.append(1)
        else:
            sizes[-1] += 1
    sizes.sort(reverse=True)
    return sizes


def major_cluster_count(opinions: Sequence[float], *, tol: float = 0.01,
                        min_size: int = 10) -> int:
    """Number of MAJOR clusters — those holding at least ``min_size`` agents.

    Deffuant et al.'s ⌊1/(2eps)⌋ law describes the major opinion groups; a naive
    total count is inflated by tiny "minor" clusters of a handful of stray agents
    that get stranded between the major peaks (a documented feature of the model,
    not a bug). ``min_size`` is the major/minor cut. NOTE (adversarial review
    2026-06-29): this cut is a POST-HOC reporting lens introduced at analysis time —
    it was NOT in the locked predictions doc (which defines only the TOTAL #clusters).
    The locked clause P1 is graded on the total count; the major-count fit is reported
    separately as the literature reading. A reporting lens on the SAME converged
    opinions, not a re-tuning of the dynamics."""
    return sum(1 for s in cluster_sizes(opinions, tol=tol) if s >= min_size)


def cluster_centers(opinions: Sequence[float], *, tol: float = 0.01) -> List[float]:
    """Mean opinion of each cluster (clusters defined as in ``count_clusters``)."""
    if not opinions:
        return []
    xs = sorted(opinions)
    centers: List[float] = []
    group = [xs[0]]
    for cur in xs[1:]:
        if cur - group[-1] > tol:
            centers.append(sum(group) / len(group))
            group = [cur]
        else:
            group.append(cur)
    centers.append(sum(group) / len(group))
    return centers


def predicted_clusters(eps: float) -> int:
    """Deffuant's approximate cluster law: #clusters ≈ ⌊1/(2·eps)⌋.

    The opinion line [0,1] partitions into bands of width ~2·eps, so ~1/(2·eps)
    surviving clusters. This is the analytic anchor the run is compared against
    (it is NOT fit to the run)."""
    return int(math.floor(1.0 / (2.0 * eps)))


def run_single(n: int = 1000, *, eps: float = 0.2, mu: float = 0.5, seed: int = 0,
               move_tol: float = 1e-6, cluster_tol: float = 0.01,
               major_min_size: int = 10, max_sweeps: int = 100_000) -> Dict[str, Any]:
    """One Deffuant run at a given seed."""
    return DeffuantModel(n, eps=eps, mu=mu, seed=seed, move_tol=move_tol,
                         cluster_tol=cluster_tol, major_min_size=major_min_size,
                         max_sweeps=max_sweeps).run()


def run_many_seeds(n: int = 1000, *, eps: float = 0.2, mu: float = 0.5,
                   n_seeds: int = 10, seed_base: int = 0, move_tol: float = 1e-6,
                   cluster_tol: float = 0.01, major_min_size: int = 10,
                   max_sweeps: int = 100_000) -> Dict[str, Any]:
    """Run ``n_seeds`` Deffuant runs (seed ``seed_base + i``) at fixed (eps, mu)
    and summarise the cluster count + convergence time across seeds.

    Returns the per-seed TOTAL #clusters and MAJOR #clusters (clusters with
    >= ``major_min_size`` agents), their means, the per-seed convergence sweeps and
    their mean, and the analytic ⌊1/(2·eps)⌋ anchor for comparison.
    """
    runs = [run_single(n, eps=eps, mu=mu, seed=seed_base + i, move_tol=move_tol,
                        cluster_tol=cluster_tol, major_min_size=major_min_size,
                        max_sweeps=max_sweeps)
            for i in range(n_seeds)]
    per_seed_clusters = [r["n_clusters"] for r in runs]
    per_seed_major = [r["n_major_clusters"] for r in runs]
    per_seed_sweeps = [r["sweeps"] for r in runs]
    return {
        "n": n,
        "eps": eps,
        "mu": mu,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "cluster_tol": cluster_tol,
        "major_min_size": major_min_size,
        "per_seed_clusters": per_seed_clusters,
        "mean_clusters": sum(per_seed_clusters) / n_seeds,
        "min_clusters": min(per_seed_clusters),
        "max_clusters": max(per_seed_clusters),
        "per_seed_major_clusters": per_seed_major,
        "mean_major_clusters": sum(per_seed_major) / n_seeds,
        "min_major_clusters": min(per_seed_major),
        "max_major_clusters": max(per_seed_major),
        "per_seed_sweeps": per_seed_sweeps,
        "mean_sweeps": sum(per_seed_sweeps) / n_seeds,
        "predicted_clusters": predicted_clusters(eps),
        "all_converged": all(r["converged"] for r in runs),
    }
