"""Public Goods Game + peer punishment — a faithful evolutionary agent-based model.

Source: Fehr, E. & Gächter, S. (2000) "Cooperation and Punishment in Public Goods
Experiments", American Economic Review 90(4):980-994; and Fehr, E. & Gächter, S.
(2002) "Altruistic punishment in humans", Nature 415:137-140. The central finding:
in a repeated public-goods game cooperation COLLAPSES without a punishment option but
is SUSTAINED once players can punish free-riders (peer/altruistic punishment).

This is the *evolutionary* agent-based abstraction of that experimental result, in the
tradition of Boyd & Richerson, Hauert/Sigmund/Brandt, and Fehr's own evolutionary
modelling: a well-mixed population of strategy agents whose strategies spread by
payoff-based imitation.

Rules (the fixed model, locked before running — see PREDICTIONS-locked.md):
  * Well-mixed population of N ``PlayerAgent``s. Strategies:
      - Cooperator (C): contributes c=1 to the group pot.
      - Defector  (D): contributes nothing.
      - Punisher  (P): contributes c=1 AND pays beta=1 for EACH defector in its group;
        each defector so punished loses gamma=3 per punisher in the group.
    (P is available ONLY in the with-punishment treatment — the single difference
    between the two FAIR treatments.)
  * Each ROUND every agent is randomly partitioned into groups of n=5. Each group
    plays one PGG: the pot = (sum of contributions) * r (r=3, the multiplier), split
    EQUALLY among the n=5 members regardless of whether they contributed. So a member's
    PGG payoff = (share of pot) - (own contribution).
  * Punishment is then applied within each group: each defector loses gamma per punisher
    in its group; each punisher pays beta per defector in its group.
  * STRATEGY UPDATE = payoff-proportional imitation (pairwise comparison): every agent
    picks one random "model" agent; if the model's round payoff is higher, the agent
    copies the model's strategy with probability proportional to the payoff difference
    (normalised by the maximum possible single-round payoff span). This is the canonical
    imitation/replicator-style update used throughout the cooperation-evolution
    literature; only payoff DIFFERENCES matter, so it handles the negative payoffs that
    punishment produces without any shifting/clipping. Deterministic given a seed.
  * Outcome (LOCKED metric) = mean cooperation = fraction of the population that
    CONTRIBUTES (cooperators + punishers), at steady state (mean over the last ticks).

The two treatments are FAIR: identical n, c, r, beta, gamma, update rule, init mixing
strategy and seeds; they differ ONLY in whether the Punisher strategy exists in the
population. No parameter is tuned to make cooperation persist (batch-2 Nowak-May lesson).

Built on the neutral platform (``abm_auto._platform``): each player is a ``PlayerAgent``
whose ``step`` stages its next strategy from this round's payoffs; the model owns the
random grouping, the PGG accounting, the synchronous strategy commit, and a
``DataCollector`` (the cooperation-fraction series) — not a hand-rolled god-loop.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

COOPERATOR = "C"
DEFECTOR = "D"
PUNISHER = "P"

# Strategies that CONTRIBUTE to the pot (the "cooperation" the metric counts).
CONTRIBUTING = frozenset({COOPERATOR, PUNISHER})


# -- Agent --------------------------------------------------------------------

class PlayerAgent(Agent):
    """One player. ``strategy`` is 'C', 'D', or 'P'; ``payoff`` is the round payoff
    (PGG share minus contribution, minus punishment costs/losses); ``_next_strategy``
    is staged during the imitation step and committed by the model so the whole
    strategy update is synchronous (every agent imitates the SAME post-round payoffs)."""

    def __init__(self, agent_id: int, model: "PublicGoodsModel", *, strategy: str) -> None:
        super().__init__(agent_id, model)
        self.strategy = strategy
        self.payoff = 0.0
        self._next_strategy = strategy

    def contributes(self) -> bool:
        return self.strategy in CONTRIBUTING

    def choose_next_strategy(self) -> None:
        """Payoff-proportional pairwise imitation: pick a random model agent; if it
        scored higher this round, copy its strategy with probability proportional to
        the payoff gap (normalised by the maximum possible single-round span). Only
        differences matter, so negative payoffs need no shifting."""
        model = self.model
        rng = model.rng
        other = model.agent_by_id[model.random_other_id(self.id)]
        gap = other.payoff - self.payoff
        if gap <= 0.0:
            self._next_strategy = self.strategy
            return
        prob = gap / model.payoff_span
        if rng.random() < prob:
            self._next_strategy = other.strategy
        else:
            self._next_strategy = self.strategy

    def step(self) -> None:
        self.choose_next_strategy()


# -- Model --------------------------------------------------------------------

class PublicGoodsModel(AgentModel):
    """Well-mixed evolutionary public-goods game with optional peer punishment.

    Construct with the population size, the PGG parameters, an initial strategy mix,
    and the treatment (``with_punishment``). ``run`` iterates ``n_rounds`` of
    (random grouping -> PGG + punishment payoffs -> synchronous imitation) and records
    the cooperation fraction (contributors / N) each round.
    """

    def __init__(self, n: int = 1000, *, group_size: int = 5, contribution: float = 1.0,
                 multiplier: float = 3.0, punish_cost: float = 1.0, punish_fine: float = 3.0,
                 with_punishment: bool = False,
                 init_mix: Optional[Dict[str, float]] = None,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n % group_size != 0:
            raise ValueError(f"n={n} must be a multiple of group_size={group_size}")
        self.n = n
        self.group_size = group_size
        self.c = float(contribution)
        self.r = float(multiplier)
        self.beta = float(punish_cost)
        self.gamma = float(punish_fine)
        self.with_punishment = with_punishment

        # Initial strategy mix. Default: equal thirds C/D/P (with punishment) or equal
        # halves C/D (no punishment) — a standard, fair seeding (NOT rigged to win).
        if init_mix is None:
            init_mix = ({COOPERATOR: 1 / 3, DEFECTOR: 1 / 3, PUNISHER: 1 / 3}
                        if with_punishment else {COOPERATOR: 0.5, DEFECTOR: 0.5})
        if not with_punishment and init_mix.get(PUNISHER, 0.0) > 0.0:
            raise ValueError("no-punishment treatment cannot seed Punishers")
        self.init_mix = dict(init_mix)

        # Maximum possible single-round payoff span (normaliser for the imitation
        # probability). Best case ~ free-riding defector in an all-contributor group of
        # n; worst case ~ a defector fully punished by (n-1) punishers. A safe, fixed
        # upper bound on |payoff gap| that does NOT depend on the realised state.
        self.payoff_span = self._max_payoff_span()

        # Build the population with the requested mix (deterministic from the seed).
        self.agent_by_id: Dict[int, PlayerAgent] = {}
        for pid, strat in enumerate(self._initial_strategies()):
            agent = PlayerAgent(pid, self, strategy=strat)
            self.agent_by_id[pid] = agent
            self.add_agent(agent)

        self.reporter = DataCollector({"coop_fraction": lambda m: m.cooperation_fraction()})

    # -- setup helpers --
    def _max_payoff_span(self) -> float:
        """A fixed upper bound on the largest possible |payoff difference| in one round,
        used only to normalise the imitation probability into [0, 1]. Largest gain a
        defector can have over a contributor in a group: free-ride share + saved
        contribution; largest loss a punished defector can take: (n-1)*gamma. We bound
        generously by the sum so prob is always in [0, 1]."""
        n = self.group_size
        max_pot_share = self.r * self.c  # whole group contributes -> share = r*c*n/n = r*c
        free_ride_gain = max_pot_share + self.c  # defector keeps c and still gets a share
        max_punish_loss = (n - 1) * self.gamma  # fully punished defector
        return free_ride_gain + max_punish_loss + 1e-9

    def _initial_strategies(self) -> List[str]:
        """Deterministic initial strategy assignment matching ``init_mix`` as closely as
        integer counts allow, then shuffled by the seeded RNG (so position carries no
        information)."""
        strategies: List[str] = []
        order = [COOPERATOR, DEFECTOR, PUNISHER]
        counts = {s: int(round(self.init_mix.get(s, 0.0) * self.n)) for s in order}
        # Fix rounding drift so the counts sum to exactly n.
        drift = self.n - sum(counts.values())
        # Apply drift to the largest-share present strategy (stable, deterministic).
        present = [s for s in order if counts[s] > 0] or [COOPERATOR]
        counts[present[0]] += drift
        for s in order:
            strategies.extend([s] * counts[s])
        self.rng.shuffle(strategies)
        return strategies

    def random_other_id(self, self_id: int) -> int:
        """A uniformly random agent id != ``self_id`` (the imitation model)."""
        rng = self.rng
        j = rng.randrange(self.n)
        while j == self_id:
            j = rng.randrange(self.n)
        return j

    # -- metrics --
    def contributor_count(self) -> int:
        return sum(1 for a in self.agent_by_id.values() if a.contributes())

    def cooperation_fraction(self) -> float:
        return self.contributor_count() / self.n if self.n else 0.0

    def strategy_counts(self) -> Dict[str, int]:
        counts = {COOPERATOR: 0, DEFECTOR: 0, PUNISHER: 0}
        for a in self.agent_by_id.values():
            counts[a.strategy] += 1
        return counts

    # -- one round of payoffs --
    def assign_payoffs(self) -> None:
        """Randomly partition the population into groups of ``group_size`` and compute
        every agent's round payoff: PGG share minus own contribution, then punishment
        (defectors lose gamma per punisher; punishers pay beta per defector)."""
        agents = self.agent_by_id
        ids = list(range(self.n))
        self.rng.shuffle(ids)
        gs = self.group_size
        for start in range(0, self.n, gs):
            group = ids[start:start + gs]
            members = [agents[i] for i in group]
            contributors = [m for m in members if m.contributes()]
            n_defectors = sum(1 for m in members if m.strategy == DEFECTOR)
            n_punishers = sum(1 for m in members if m.strategy == PUNISHER)
            pot = self.r * self.c * len(contributors)
            share = pot / gs
            for m in members:
                # PGG: everyone gets an equal share; contributors paid c.
                pay = share - (self.c if m.contributes() else 0.0)
                if m.strategy == DEFECTOR:
                    pay -= self.gamma * n_punishers          # fined by each punisher
                elif m.strategy == PUNISHER:
                    pay -= self.beta * n_defectors           # pays to punish each defector
                m.payoff = pay

    # -- tick --
    def step(self) -> None:
        """One round: (1) random grouping + PGG/punishment payoffs against the CURRENT
        population; (2) every agent stages its next strategy by payoff-proportional
        imitation; (3) synchronous commit; (4) record + advance t."""
        self.assign_payoffs()
        self.agents.step()                       # stage next strategies from this round
        for a in self.agent_by_id.values():
            a.strategy = a._next_strategy
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_rounds: int = 300) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate ``n_rounds`` rounds; return a run summary with the full
        cooperation-fraction series (t=0 baseline + every round) and final strategy mix."""
        self.reporter.collect(self)              # t=0 baseline (initial mix)
        for _ in range(n_rounds):
            self.step()
        series = self.reporter.series("coop_fraction")
        return {
            "n": self.n,
            "group_size": self.group_size,
            "with_punishment": self.with_punishment,
            "params": {"c": self.c, "r": self.r, "beta": self.beta, "gamma": self.gamma},
            "init_mix": self.init_mix,
            "n_rounds": n_rounds,
            "coop_series": series,
            "final_coop_fraction": series[-1],
            "final_strategy_counts": self.strategy_counts(),
        }


# -- sweep / summary helpers --------------------------------------------------

def steady_state_fraction(series: List[float], *, last: int = 50) -> float:
    """Mean cooperation fraction over the last ``last`` recorded rounds (the
    statistical steady state). Falls back to the whole series if it is shorter."""
    tail = series[-last:] if len(series) >= last else series
    return sum(tail) / len(tail) if tail else 0.0


def run_treatment_seeds(*, with_punishment: bool, n: int = 1000, group_size: int = 5,
                        contribution: float = 1.0, multiplier: float = 3.0,
                        punish_cost: float = 1.0, punish_fine: float = 3.0,
                        init_mix: Optional[Dict[str, float]] = None,
                        n_rounds: int = 300,
                        seeds: Tuple[int, ...] = tuple(range(10)),
                        last: int = 50) -> Dict[str, Any]:
    """Run one treatment over several seeds; report per-seed steady-state cooperation
    fraction + trajectories + the aggregate mean/min/max. The two treatments call this
    with identical params and seeds, differing ONLY in ``with_punishment``."""
    per_seed = []
    for s in seeds:
        res = PublicGoodsModel(
            n=n, group_size=group_size, contribution=contribution, multiplier=multiplier,
            punish_cost=punish_cost, punish_fine=punish_fine,
            with_punishment=with_punishment, init_mix=init_mix, seed=s,
        ).run(n_rounds)
        ss = steady_state_fraction(res["coop_series"], last=last)
        per_seed.append({
            "seed": s,
            "steady_state": ss,
            "final": res["final_coop_fraction"],
            "final_strategy_counts": res["final_strategy_counts"],
            "coop_series": res["coop_series"],
        })
    ss_vals = [r["steady_state"] for r in per_seed]
    return {
        "with_punishment": with_punishment,
        "n": n, "group_size": group_size,
        "params": {"c": contribution, "r": multiplier, "beta": punish_cost, "gamma": punish_fine},
        "n_rounds": n_rounds, "seeds": list(seeds), "last": last,
        "per_seed": per_seed,
        "mean_steady_state": sum(ss_vals) / len(ss_vals),
        "min_steady_state": min(ss_vals),
        "max_steady_state": max(ss_vals),
        "mean_trajectory": _mean_trajectory([r["coop_series"] for r in per_seed]),
    }


def _mean_trajectory(series_list: List[List[float]]) -> List[float]:
    """Element-wise mean over equal-length cooperation-fraction series (the seed-averaged
    trajectory). Assumes all series share the same length (same n_rounds)."""
    if not series_list:
        return []
    length = len(series_list[0])
    k = len(series_list)
    return [sum(s[t] for s in series_list) / k for t in range(length)]
