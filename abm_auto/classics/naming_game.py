"""Minimal Naming Game — a faithful agent-based reproduction (Baronchelli et al. 2006).

Source: Baronchelli, A., Felici, M., Loreto, V., Caglioti, E. & Steels, L. (2006)
"Sharp transition towards shared vocabularies in multi-agent systems",
J. Stat. Mech. P06014. doi:10.1088/1742-5468/2006/06/P06014. See also Steels, L.
(1995) "A self-organizing spatial vocabulary", Artificial Life 2(3):319-332.

The minimal Naming Game: a population of N agents must reach consensus on a shared
name for ONE object, using only pairwise local interactions and no central control.
The signature result is that local negotiation drives the population to GLOBAL
consensus through a characteristic vocabulary build-up (total #words and #distinct
names peak, then collapse to a single shared name held by all).

Rules (faithful to the minimal NG, asynchronous / pairwise):
  * N agents, each a ``NamerAgent`` carrying an ``inventory`` = a set of names
    (strings/ints) for the one shared object. All inventories start EMPTY.
  * One INTERACTION: pick a random ordered pair (speaker, hearer), speaker != hearer.
    - The speaker UTTERS a name: if its inventory is empty it INVENTS a brand-new
      globally-unique name (and adds it to its own inventory); otherwise it picks a
      name uniformly at random from its inventory.
    - If the hearer HAS the uttered name in its inventory  →  SUCCESS: BOTH speaker
      and hearer delete ALL of their names except the uttered one (collapse to it).
    - Else  →  FAILURE: the hearer ADDS the uttered name to its inventory (the
      speaker is unchanged).
  * The all-agree-on-one-name state is ABSORBING: once every inventory is the same
    single name, every utterance is that name and every interaction is a no-op
    success. Run until global consensus or a generous step cap.
  * Outcome per run = consensus reached + the trajectories of total #words (sum of
    inventory sizes) and #distinct names over time, and the #interactions to
    consensus.

Built on the neutral platform (``abm_auto._platform``): each agent is a ``NamerAgent``
holding its own ``inventory``; the model drives the random-pair interactions and uses
an ``AgentSet`` only as the agent registry. ``DataCollector`` records the per-tick
metrics. Given a seed the whole run is reproducible (one seeded RNG chain).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class NamerAgent(Agent):
    """One namer holding an ``inventory`` (a set of names) for the one shared object.

    The agent is passive in the asynchronous Naming Game: it does not ``step`` on a
    schedule. When the model selects it as speaker it ``utter``s a name; when selected
    as hearer it either collapses (``adopt_success``) or grows (``hear_failure``). Each
    method reads/writes only this agent's own ``inventory`` (no global state consulted).
    ``step`` is intentionally a no-op so the platform scheduler is never the driver.
    """

    def __init__(self, agent_id: int, model: "NamingGameModel") -> None:
        super().__init__(agent_id, model)
        self.inventory: set = set()

    def utter(self) -> Any:
        """Return a name to say. If empty, invent a fresh globally-unique name (and add
        it to own inventory); else pick one uniformly at random from own inventory.

        Reads only this agent's inventory; uses the model RNG + invention counter so the
        whole run stays deterministic given a seed."""
        if not self.inventory:
            name = self.model.invent_name()
            self.inventory.add(name)
            return name
        # uniform random pick from own inventory (sorted for deterministic indexing)
        names = sorted(self.inventory, key=repr)
        return names[self.model.rng.randrange(len(names))]

    def adopt_success(self, name: Any) -> None:
        """SUCCESS: collapse own inventory to exactly the agreed name."""
        self.inventory = {name}

    def hear_failure(self, name: Any) -> None:
        """FAILURE: add the uttered name to own inventory (speaker unchanged)."""
        self.inventory.add(name)

    def step(self) -> None:  # asynchronous model: the model drives interactions
        pass


# -- Model --------------------------------------------------------------------

class NamingGameModel(AgentModel):
    """Drives a well-mixed minimal Naming Game to global consensus.

    Construct with N, a seed, and an optional step cap. ``run`` performs random ordered
    pairwise interactions until the population reaches global consensus (every agent's
    inventory is exactly the same single name) or the cap, then returns a summary dict
    (consensus reached, the name, #interactions to consensus, and the total-words /
    distinct-names trajectories sampled per "sweep" of N interactions plus the final).
    """

    def __init__(self, *, n: int = 1000, seed: int = 0,
                 max_steps: Optional[int] = None,
                 sample_every: Optional[int] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n < 2:
            raise ValueError(f"n must be >= 2; got {n}")
        self.n = n
        # Generous cap chosen BEFORE running: the minimal NG converges in O(N^1.5)
        # SUCCESSFUL interactions (well below ~N^2). 1000*N interactions for N=1000 is
        # 1e6 — comfortably above the convergence time, so a genuine run is never
        # truncated, while a (theoretically impossible) non-converging run still halts.
        self.max_steps = max_steps if max_steps is not None else 1000 * n
        # Sample the trajectories once per "sweep" of N interactions (keeps results.json
        # compact at N=1000 while still capturing the peak-then-collapse shape).
        self.sample_every = sample_every if sample_every is not None else n

        self._name_counter = 0          # monotonic invention counter -> unique names

        self.namers: List[NamerAgent] = []
        for k in range(n):
            a = NamerAgent(k, self)
            self.namers.append(a)
            self.add_agent(a)

        # DataCollector over the platform metrics (records appended once per sample).
        self.reporter = DataCollector({
            "interaction": lambda m: m._interactions,
            "total_words": lambda m: m.total_words(),
            "distinct_names": lambda m: m.distinct_names(),
            "success_rate": lambda m: m.recent_success_rate(),
        })
        self._interactions = 0
        # success bookkeeping for the running success-rate metric (over the last sweep)
        self._succ_window = 0
        self._inter_window = 0
        self._last_success_rate = 0.0

    # -- invention --
    def invent_name(self) -> int:
        """Return a brand-new globally-unique name (a monotonically increasing int)."""
        name = self._name_counter
        self._name_counter += 1
        return name

    # -- metrics --
    def total_words(self) -> int:
        """Sum of inventory sizes over all agents (the total vocabulary in the system)."""
        return sum(len(a.inventory) for a in self.namers)

    def distinct_names(self) -> int:
        """Number of distinct names present anywhere in the population."""
        seen: set = set()
        for a in self.namers:
            seen |= a.inventory
        return len(seen)

    def recent_success_rate(self) -> float:
        """Fraction of recent interactions (the current sample window) that succeeded."""
        return self._last_success_rate

    def consensus_name(self) -> Optional[Any]:
        """The single shared name if the population is at global consensus, else None.

        Global consensus = every agent's inventory is exactly the SAME single name."""
        first = self.namers[0].inventory
        if len(first) != 1:
            return None
        name = next(iter(first))
        for a in self.namers:
            if a.inventory != first:
                return None
        return name

    def at_consensus(self) -> bool:
        return self.consensus_name() is not None

    # -- one asynchronous interaction --
    def interact(self) -> bool:
        """One pairwise Naming-Game interaction. Returns True on SUCCESS.

        Picks a random ordered pair (speaker != hearer); speaker utters a name; on a
        hearer-match BOTH collapse to it (success), else the hearer adds it (failure)."""
        i = self.rng.randrange(self.n)
        j = self.rng.randrange(self.n)
        while j == i:
            j = self.rng.randrange(self.n)
        speaker = self.namers[i]
        hearer = self.namers[j]
        name = speaker.utter()
        if name in hearer.inventory:
            speaker.adopt_success(name)
            hearer.adopt_success(name)
            success = True
        else:
            hearer.hear_failure(name)
            success = False
        self._interactions += 1
        self._inter_window += 1
        if success:
            self._succ_window += 1
        return success

    # -- run --
    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Perform pairwise interactions until global consensus or the cap; return the
        run summary. Consensus is checked after every interaction so the interaction
        count reflects the exact step at which consensus was reached. Trajectories are
        sampled once per ``sample_every`` interactions (plus a t=0 baseline + final)."""
        # t=0 baseline (all inventories empty).
        self.reporter.collect(self)
        reached = self.at_consensus()
        while not reached and self._interactions < self.max_steps:
            self.interact()
            if self._interactions % self.sample_every == 0:
                self._last_success_rate = (
                    self._succ_window / self._inter_window if self._inter_window else 0.0
                )
                self._succ_window = 0
                self._inter_window = 0
                self.reporter.collect(self)
            if self.at_consensus():
                reached = True
        # final sample (captures the exact consensus / cap state).
        if self._inter_window:
            self._last_success_rate = self._succ_window / self._inter_window
        self.reporter.collect(self)

        name = self.consensus_name()
        total_words_series = self.reporter.series("total_words")
        distinct_series = self.reporter.series("distinct_names")
        return {
            "n": self.n,
            "seed_used": True,
            "reached_consensus": reached,
            "consensus_name": name,
            "interactions_to_consensus": self._interactions if reached else None,
            "total_interactions": self._interactions,
            "capped": not reached,
            "final_total_words": self.total_words(),
            "final_distinct_names": self.distinct_names(),
            "peak_total_words": max(total_words_series) if total_words_series else 0,
            "peak_distinct_names": max(distinct_series) if distinct_series else 0,
            "total_words_series": total_words_series,
            "distinct_names_series": distinct_series,
            "success_rate_series": self.reporter.series("success_rate"),
            "interaction_series": self.reporter.series("interaction"),
        }


# -- sweep helpers ------------------------------------------------------------

def run_single(*, n: int = 1000, seed: int = 0,
               max_steps: Optional[int] = None,
               sample_every: Optional[int] = None) -> Dict[str, Any]:
    """One Naming-Game run to consensus (or the cap)."""
    return NamingGameModel(n=n, seed=seed, max_steps=max_steps,
                           sample_every=sample_every).run()


def run_many_seeds(*, n: int = 1000, n_runs: int = 10, seed_base: int = 0,
                   max_steps: Optional[int] = None,
                   sample_every: Optional[int] = None) -> Dict[str, Any]:
    """Run ``n_runs`` independent Naming-Game realisations and summarise.

    Each run uses seed ``seed_base + i`` (deterministic ensemble). Returns the consensus
    fraction (P1), per-run peaks of #distinct names and total words (P2/P3), the final
    #distinct names and total words, and convergence-time statistics over the runs that
    reached consensus. Per-run records carry the trajectories for results.json.
    """
    consensus_reached = 0
    conv_times: List[int] = []
    peak_distinct: List[int] = []
    peak_words: List[int] = []
    final_distinct: List[int] = []
    final_words: List[int] = []
    per_run: List[Dict[str, Any]] = []

    for i in range(n_runs):
        seed = seed_base + i
        res = run_single(n=n, seed=seed, max_steps=max_steps, sample_every=sample_every)
        if res["reached_consensus"]:
            consensus_reached += 1
            conv_times.append(res["interactions_to_consensus"])
        peak_distinct.append(res["peak_distinct_names"])
        peak_words.append(res["peak_total_words"])
        final_distinct.append(res["final_distinct_names"])
        final_words.append(res["final_total_words"])
        per_run.append({
            "seed": seed,
            "reached_consensus": res["reached_consensus"],
            "consensus_name": res["consensus_name"],
            "interactions_to_consensus": res["interactions_to_consensus"],
            "total_interactions": res["total_interactions"],
            "capped": res["capped"],
            "peak_distinct_names": res["peak_distinct_names"],
            "peak_total_words": res["peak_total_words"],
            "final_distinct_names": res["final_distinct_names"],
            "final_total_words": res["final_total_words"],
            "total_words_series": res["total_words_series"],
            "distinct_names_series": res["distinct_names_series"],
            "success_rate_series": res["success_rate_series"],
            "interaction_series": res["interaction_series"],
        })

    def _stats(xs: List[float]) -> Dict[str, float]:
        if not xs:
            return {"mean": 0.0, "min": 0.0, "max": 0.0, "var": 0.0, "n": 0}
        mean = sum(xs) / len(xs)
        var = sum((x - mean) ** 2 for x in xs) / len(xs)
        return {"mean": mean, "min": min(xs), "max": max(xs), "var": var, "n": len(xs)}

    return {
        "n": n,
        "n_runs": n_runs,
        "seed_base": seed_base,
        "n_consensus": consensus_reached,
        "consensus_fraction": consensus_reached / n_runs,
        "convergence_interactions": _stats(conv_times),
        "peak_distinct_names": _stats(peak_distinct),
        "peak_total_words": _stats(peak_words),
        "final_distinct_names": _stats(final_distinct),
        "final_total_words": _stats(final_words),
        "per_run": per_run,
    }
