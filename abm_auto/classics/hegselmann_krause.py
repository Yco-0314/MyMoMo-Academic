"""Hegselmann–Krause (2002) bounded-confidence opinion dynamics — a faithful
agent-based reproduction.

Source: Hegselmann, R. & Krause, U. (2002) "Opinion dynamics and bounded
confidence: models, analysis and simulation", Journal of Artificial Societies and
Social Simulation (JASSS) 5(3).

Rules (verified against the paper):
  * N agents, each holding a continuous opinion ``x`` drawn ~ Uniform[0, 1].
  * The dynamics are a SYNCHRONOUS sweep (NOT pairwise random encounters — this is
    the defining contrast with Deffuant). In one tick EVERY agent simultaneously
    replaces its opinion with the AVERAGE of all agents whose opinion is currently
    within the confidence bound ``eps`` of its own (INCLUDING ITSELF):

        x_i(t+1) = mean{ x_j(t) : |x_i(t) - x_j(t)| <= eps }

    All updates read the SAME snapshot ``x(t)`` and are committed together, so the
    update is order-independent and deterministic given the initial draw.
  * The model runs until a stationary state — the largest single opinion change in a
    whole synchronous sweep drops below a tiny tolerance ``move_tol`` — or a step cap.
  * Outcome = the number of final opinion CLUSTERS: sort the converged opinions and
    count maximal runs whose consecutive gaps are within a small tolerance (0.01).

Boundary convention: the confidence bound is INCLUSIVE (``<= eps``), per the HK
definition (the closed confidence interval [x_i - eps, x_i + eps]). This differs
deliberately from the strict ``< eps`` in this repo's Deffuant module; both follow
their respective papers.

Locality note (no global oracle): each agent's update reads only the opinions that
lie within its own ``eps``-neighbourhood (a confidence-bounded view of the population)
and writes only its own opinion. There is no population-level statistic in the update
rule — the "average" is over the agent's confidence set, not over everyone. The
neighbourhood is recomputed every tick from the current opinions (HK's mean-field
"fully informed within confidence" view), so it is dynamic rather than a fixed graph.
Given a seed the whole run is reproducible.

Built on the neutral platform (``abm_auto._platform``): each agent is an
``OpinionAgent`` carrying its scalar opinion; ``HegselmannKrauseModel`` drives the
synchronous sweeps over the ``AgentSet`` roster and records (via a ``DataCollector``)
the per-sweep max opinion change and the running cluster count.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class OpinionAgent(Agent):
    """One agent carrying a continuous opinion ``x`` in [0, 1].

    The agent is the STATE holder. In HK's synchronous dynamics the update of one
    agent depends on the *snapshot* of all opinions at the start of the tick, so the
    per-agent ``step`` cannot mutate state mid-sweep (that would let earlier agents'
    new opinions leak into later agents' averages, which is the Deffuant/sequential
    behaviour, NOT HK). The synchronous two-phase update therefore lives on the model
    (``step``): phase 1 computes every agent's next opinion from the shared snapshot,
    phase 2 commits them together.
    """

    def __init__(self, agent_id: int, model: "HegselmannKrauseModel", *,
                 opinion: float) -> None:
        super().__init__(agent_id, model)
        self.x = opinion

    def step(self) -> None:  # pragma: no cover - HK updates synchronously on the model
        """HK commits all agents from one shared snapshot, so the per-agent ``step``
        is intentionally a no-op; the model's ``step`` (one synchronous sweep) is the
        tick."""
        return None


# -- Model --------------------------------------------------------------------

class HegselmannKrauseModel(AgentModel):
    """Drives Hegselmann–Krause bounded-confidence dynamics to a stationary state.

    Construct with N, the confidence threshold ``eps``, and a seed. ``run`` iterates
    synchronous sweeps (each sweep = every agent simultaneously averages its
    confidence-set) until the largest single opinion change in a whole sweep falls
    below ``move_tol`` (stationary) or ``max_sweeps`` is reached, then returns a
    summary dict (final opinions, #clusters, sweeps, per-sweep max-move series).
    """

    def __init__(self, n: int = 1000, *, eps: float = 0.2, seed: int = 0,
                 move_tol: float = 1e-6, cluster_tol: float = 0.01,
                 max_sweeps: int = 100_000) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.seed_value = seed
        self.n = n
        self.eps = eps
        self.move_tol = move_tol
        self.cluster_tol = cluster_tol
        self.max_sweeps = max_sweeps

        #: Largest single opinion change in the sweep just committed (stationary
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

    # -- metrics --
    def opinions(self) -> List[float]:
        return [a.x for a in self.agent_list]

    def cluster_count(self) -> int:
        """Number of final opinion clusters: sort opinions and count maximal runs
        whose consecutive gaps are <= ``cluster_tol``."""
        return count_clusters(self.opinions(), tol=self.cluster_tol)

    # -- the synchronous HK sweep --
    def step(self) -> None:
        """One synchronous sweep. Phase 1: from the shared snapshot ``x(t)`` compute
        every agent's next opinion as the mean of its confidence set (all agents
        within ``eps``, inclusive, INCLUDING itself). Phase 2: commit all next
        opinions together and record the largest single change (the stationary
        signal). Order-independent because phase 1 never reads phase-2 writes."""
        snapshot = [a.x for a in self.agent_list]
        eps = self.eps
        next_opinions = [_confidence_mean(xi, snapshot, eps) for xi in snapshot]

        max_move = 0.0
        for agent, xi, new_x in zip(self.agent_list, snapshot, next_opinions):
            move = abs(new_x - xi)
            if move > max_move:
                max_move = move
            agent.x = new_x
        self._sweep_max_move = max_move
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate synchronous sweeps until stationary (a whole sweep's max move <
        move_tol) or ``max_sweeps``; return the run summary."""
        for _ in range(self.max_sweeps):
            self.step()
            if self._sweep_max_move < self.move_tol:
                break
        final = self.opinions()
        n_clusters = count_clusters(final, tol=self.cluster_tol)
        return {
            "n": self.n,
            "eps": self.eps,
            "seed": self.seed_value,
            "cluster_tol": self.cluster_tol,
            "move_tol": self.move_tol,
            "sweeps": self.t,
            "converged": self._sweep_max_move < self.move_tol,
            "n_clusters": n_clusters,
            "is_consensus": n_clusters == 1,
            "cluster_sizes": cluster_sizes(final, tol=self.cluster_tol),
            "cluster_centers": cluster_centers(final, tol=self.cluster_tol),
            "final_opinions": final,
            "max_move_series": self.reporter.series("max_move"),
            "cluster_series": self.reporter.series("clusters"),
        }


# -- the elementary HK update (free function so it is unit-testable) -----------

def _confidence_mean(xi: float, snapshot: Sequence[float], eps: float) -> float:
    """The HK update for one agent: mean of all opinions within ``eps`` of ``xi``
    (inclusive bound ``<= eps``), INCLUDING ``xi`` itself. ``xi`` is always in its
    own confidence set (|xi - xi| = 0 <= eps), so the denominator is never zero."""
    total = 0.0
    count = 0
    for xj in snapshot:
        if abs(xi - xj) <= eps:
            total += xj
            count += 1
    return total / count


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


def run_single(n: int = 1000, *, eps: float = 0.2, seed: int = 0,
               move_tol: float = 1e-6, cluster_tol: float = 0.01,
               max_sweeps: int = 100_000) -> Dict[str, Any]:
    """One HK run at a given seed."""
    return HegselmannKrauseModel(n, eps=eps, seed=seed, move_tol=move_tol,
                                 cluster_tol=cluster_tol,
                                 max_sweeps=max_sweeps).run()


def run_many_seeds(n: int = 1000, *, eps: float = 0.2, n_seeds: int = 20,
                   seed_base: int = 0, move_tol: float = 1e-6,
                   cluster_tol: float = 0.01,
                   max_sweeps: int = 100_000) -> Dict[str, Any]:
    """Run ``n_seeds`` HK runs (seed ``seed_base + i``) at fixed ``eps`` and
    summarise the cluster count + consensus fraction across seeds.

    Returns the per-seed #clusters, their mean/min/max/variance, the per-seed
    consensus flag (#clusters == 1) and the consensus FRACTION (share of seeds that
    reached a single cluster), and the per-seed convergence sweeps + their mean.
    """
    runs = [run_single(n, eps=eps, seed=seed_base + i, move_tol=move_tol,
                       cluster_tol=cluster_tol, max_sweeps=max_sweeps)
            for i in range(n_seeds)]
    per_seed_clusters = [r["n_clusters"] for r in runs]
    per_seed_consensus = [r["is_consensus"] for r in runs]
    per_seed_sweeps = [r["sweeps"] for r in runs]
    mean_clusters = sum(per_seed_clusters) / n_seeds
    var_clusters = (sum((c - mean_clusters) ** 2 for c in per_seed_clusters)
                    / n_seeds)
    return {
        "n": n,
        "eps": eps,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "cluster_tol": cluster_tol,
        "per_seed_clusters": per_seed_clusters,
        "mean_clusters": mean_clusters,
        "var_clusters": var_clusters,
        "min_clusters": min(per_seed_clusters),
        "max_clusters": max(per_seed_clusters),
        "per_seed_consensus": per_seed_consensus,
        "n_consensus": sum(per_seed_consensus),
        "consensus_fraction": sum(per_seed_consensus) / n_seeds,
        "per_seed_sweeps": per_seed_sweeps,
        "mean_sweeps": sum(per_seed_sweeps) / n_seeds,
        "all_converged": all(r["converged"] for r in runs),
    }
