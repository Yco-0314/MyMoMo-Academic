"""Ant double-bridge foraging (Deneubourg / Goss 1989) — a faithful agent-based reproduction.

Source: Goss, S., Aron, S., Deneubourg, J.-L. & Pasteels, J.-M. (1989), "Self-organized
shortcuts in the Argentine ant", Naturwissenschaften 76:579-581.
doi:10.1007/BF00462870. (The "double-bridge" experiment + Deneubourg's choice model.)

The experiment.  A nest and a food source are joined by a bridge that splits into TWO
branches — a SHORT one (length ``Ls``) and a LONG one (length ``Ll``). Argentine ants
leaving the nest reach a fork and must choose a branch. Initially the choice is ~50/50,
but ants that take the short branch reach the food and return SOONER, so they lay
returning pheromone on the short branch earlier; the next ants are then biased toward it,
which biases the deposition further. The colony self-organizes onto the SHORT branch even
though no ant measures any length.

Deneubourg's choice rule (verified against the model in the paper).  An ant at the fork
picks the short (s) vs long (l) branch with probability proportional to a power of the
branch's pheromone plus a constant ``k``:

    P(short) = (phi_s + k)^alpha / [ (phi_s + k)^alpha + (phi_l + k)^alpha ]

``k`` is the attraction of an unmarked branch (so an unmarked fork is ~50/50) and
``alpha`` (≈2) is the non-linearity that makes the choice sharpen as one branch
accumulates more pheromone — the autocatalysis. With these constants (k≈20, alpha≈2) the
original paper reproduces the observed short-branch selection.

This reproduction (the genuine agent-based mechanics).
  * Each ``AntAgent`` carries a phase: HOMEBOUND-at-nest, OUTBOUND on a branch, or
    INBOUND on a branch, plus the branch it committed to and a countdown of ticks left to
    traverse it. Time to traverse a branch is PROPORTIONAL to its length (``travel_time =
    round(speed * length)``), so the short branch is genuinely faster to cross — that, not
    any global knowledge, is what makes it win.
  * Ants enter the bridge as a STREAM, not a simultaneous mob: at most
    ``inject_per_tick`` idle ants depart the nest per tick (the foragers queue at the nest
    and leave a few at a time, as in the experiment). When an idle ant departs it CHOOSES a
    branch with Deneubourg's rule above (reading the current pheromone on the two
    branches), commits to it, and starts an OUTBOUND traversal. On ARRIVING at the food it
    turns around and starts an INBOUND traversal of the SAME branch. On arriving home it
    deposits and rejoins the queue at the nest. (Releasing the whole colony at once instead
    would let the very first random 50/50 cohort, not the faster short-branch return, set
    the trail — an artifact; a metered stream lets the short branch's earlier return express
    itself, which is the actual Goss mechanism.)
  * PHEROMONE deposition: a fixed amount ``q`` is laid on the branch an ant traverses. By
    default ants deposit on BOTH legs (outbound arrival + inbound arrival) — the "lay on
    the way there and back" convention of the trail-laying ant; set ``deposit_on`` to
    ``"return"`` to lay only on the homeward leg (Goss's returning-ant emphasis) or
    ``"outbound"`` for the outward leg only. The convention is documented and FIXED per run.
  * EVAPORATION: at the end of every tick each reservoir decays, ``phi *= (1 - rho)``.
    Evaporation is what lets a wrong early lead be overcome and what bounds the trail.

The locked grading metric: the SHORT-PATH TRAFFIC FRACTION — of the branch *commitments*
made in a trailing window of recent departures, the fraction that chose the short branch.
(Traffic = ants actually entering a branch, the observable in the experiment.) A run also
records each reservoir's pheromone over time. Deneubourg/Goss result: with asymmetric
branches this fraction climbs above ~0.8; with symmetric branches the colony still breaks
symmetry onto ONE branch (which one is seed-dependent), rather than splitting 50/50.

Built on the neutral platform (``abm_auto._platform``): each forager is an ``AntAgent``;
``AntColonyModel`` owns the two reservoirs, drives the per-tick traversal/choice/deposit/
evaporation update over the ``AgentSet`` roster, and records (via a ``DataCollector``) the
per-tick short-path traffic fraction and the two pheromone levels. Deterministic given a
seed.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from abm_auto._platform import Agent, AgentModel, DataCollector

SHORT = 0
LONG = 1
_BRANCHES = (SHORT, LONG)

# ant phases
AT_NEST = "at_nest"
OUTBOUND = "outbound"
INBOUND = "inbound"

_DEPOSIT_MODES = ("both", "outbound", "return")


# -- Agent --------------------------------------------------------------------

class AntAgent(Agent):
    """One forager. Carries its phase (at nest / outbound / inbound), the branch it has
    committed to this trip, and ``ticks_left`` — the countdown of ticks remaining to
    finish traversing the current branch (set to that branch's travel time on departure /
    turnaround). The actual choice / deposit / evaporation is driven by the model tick so
    that all ants read a consistent start-of-tick pheromone snapshot when they depart."""

    def __init__(self, agent_id: int, model: "AntColonyModel") -> None:
        super().__init__(agent_id, model)
        self.phase = AT_NEST
        self.branch: Optional[int] = None
        self.ticks_left = 0

    def step(self) -> None:  # pragma: no cover - the tick lives on the model
        """The colony tick (depart/choose, advance traversals, deposit, evaporate) is a
        model-level update, not an autonomous single-agent step, so this is a no-op."""
        return None


# -- choice rule --------------------------------------------------------------

def choice_prob_short(phi_s: float, phi_l: float, *, k: float, alpha: float) -> float:
    """Deneubourg's branch-choice probability of the SHORT branch:

        P(short) = (phi_s + k)^alpha / [ (phi_s + k)^alpha + (phi_l + k)^alpha ].

    ``k`` > 0 is the unmarked-branch attraction (phi_s=phi_l=0 -> 0.5), ``alpha`` the
    non-linearity. Pure function of the two reservoir levels and the two constants."""
    a = (phi_s + k) ** alpha
    b = (phi_l + k) ** alpha
    total = a + b
    if total <= 0.0:                      # only if k==0 and both empty; fall back to 50/50
        return 0.5
    return a / total


# -- Model --------------------------------------------------------------------

class AntColonyModel(AgentModel):
    """Drives the double-bridge foraging dynamics over a colony of ``AntAgent``s.

    Construct with the number of ants, the two branch lengths (``len_short`` <=
    ``len_long``), the choice constants ``k`` / ``alpha``, the per-traversal deposit ``q``,
    the evaporation rate ``rho`` per tick, a traversal ``speed`` (ticks per unit length),
    the deposit convention, and a seed. ``run(n_ticks)`` advances the tick and records the
    per-tick short-path traffic fraction (over a trailing window of recent commitments) and
    the two pheromone reservoir levels.
    """

    def __init__(self, n_ants: int = 64, *, len_short: float = 1.0, len_long: float = 2.0,
                 k: float = 20.0, alpha: float = 2.0, q: float = 1.0, rho: float = 0.02,
                 speed: float = 10.0, deposit_on: str = "both", inject_per_tick: int = 2,
                 traffic_window: int = 200, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n_ants <= 0:
            raise ValueError(f"need n_ants > 0 (got {n_ants})")
        if len_short <= 0 or len_long <= 0:
            raise ValueError(f"need positive branch lengths (got {len_short}, {len_long})")
        if len_long < len_short:
            raise ValueError(
                f"len_long must be >= len_short (got short={len_short}, long={len_long})")
        if k < 0 or alpha < 0:
            raise ValueError(f"need k>=0, alpha>=0 (got k={k}, alpha={alpha})")
        if q < 0:
            raise ValueError(f"need q>=0 (got q={q})")
        if not (0.0 <= rho < 1.0):
            raise ValueError(f"need 0<=rho<1 (got {rho})")
        if speed <= 0:
            raise ValueError(f"need speed>0 (got {speed})")
        if deposit_on not in _DEPOSIT_MODES:
            raise ValueError(f"deposit_on must be one of {_DEPOSIT_MODES} (got {deposit_on!r})")
        if inject_per_tick <= 0:
            raise ValueError(f"need inject_per_tick>0 (got {inject_per_tick})")
        if traffic_window <= 0:
            raise ValueError(f"need traffic_window>0 (got {traffic_window})")

        self.seed_value = seed
        self.n_ants = n_ants
        self.lengths = {SHORT: float(len_short), LONG: float(len_long)}
        self.k = float(k)
        self.alpha = float(alpha)
        self.q = float(q)
        self.rho = float(rho)
        self.speed = float(speed)
        self.deposit_on = deposit_on
        self.inject_per_tick = inject_per_tick
        self.traffic_window = traffic_window

        # travel time per branch (ticks), proportional to length; >=1 so a traversal always
        # takes at least one tick (the short branch is still strictly faster than the long).
        self.travel_time = {
            b: max(1, round(self.speed * self.lengths[b])) for b in _BRANCHES
        }

        # two pheromone reservoirs, one per branch, start empty.
        self.pheromone: Dict[int, float] = {SHORT: 0.0, LONG: 0.0}

        # rolling record of recent branch *commitments* (departures): the traffic stream.
        self._recent_choices: List[int] = []
        self.total_choices = 0
        self.total_choices_short = 0

        self.ant_list: List[AntAgent] = []
        for i in range(n_ants):
            ant = AntAgent(i, self)
            self.ant_list.append(ant)
            self.add_agent(ant)

        self.reporter = DataCollector({
            "short_fraction": lambda m: m.short_traffic_fraction(),
            "phi_short": lambda m: m.pheromone[SHORT],
            "phi_long": lambda m: m.pheromone[LONG],
        })

    # -- metrics --
    def short_traffic_fraction(self) -> float:
        """Fraction of the most recent ``traffic_window`` branch commitments that chose the
        SHORT branch. Returns 0.5 before any ant has departed (a neutral, no-information
        baseline rather than a spurious 0/1)."""
        if not self._recent_choices:
            return 0.5
        window = self._recent_choices[-self.traffic_window:]
        return sum(1 for b in window if b == SHORT) / len(window)

    def _deposit(self, branch: int) -> None:
        self.pheromone[branch] += self.q

    # -- tick --
    def step(self) -> None:
        """One colony tick.

        (1) DEPART/CHOOSE: up to ``inject_per_tick`` ants currently at the nest read the
            SAME start-of-tick pheromone snapshot, pick a branch by Deneubourg's rule,
            commit to it (recorded as one unit of traffic), and start an OUTBOUND traversal
            with that branch's travel time. Metering the stream (a few ants per tick, not the
            whole queue) is what lets the short branch's earlier return — not the first
            random cohort — set the trail. Reading one snapshot makes a tick
            order-independent (hence deterministic given the seeded RNG draw sequence).
        (2) ADVANCE: every traversing ant's countdown ticks down by one. An OUTBOUND ant
            that arrives (countdown hits 0) deposits-if-configured, turns around, and starts
            an INBOUND traversal of the same branch. An INBOUND ant that arrives
            deposits-if-configured and becomes idle at the nest.
        (3) EVAPORATE: each reservoir decays by the factor (1 - rho).
        """
        snap_s = self.pheromone[SHORT]
        snap_l = self.pheromone[LONG]
        p_short = choice_prob_short(snap_s, snap_l, k=self.k, alpha=self.alpha)

        # (1) departures from the nest — choose against the frozen snapshot, metered to at
        # most ``inject_per_tick`` ants this tick (the foragers leave as a stream).
        injected = 0
        for ant in self.ant_list:
            if ant.phase == AT_NEST:
                if injected >= self.inject_per_tick:
                    break
                branch = SHORT if self.rng.random() < p_short else LONG
                ant.branch = branch
                ant.phase = OUTBOUND
                ant.ticks_left = self.travel_time[branch]
                self._recent_choices.append(branch)
                self.total_choices += 1
                if branch == SHORT:
                    self.total_choices_short += 1
                injected += 1

        # (2) advance traversals; handle arrivals (turnaround / home).
        deposit_out = self.deposit_on in ("both", "outbound")
        deposit_in = self.deposit_on in ("both", "return")
        for ant in self.ant_list:
            if ant.phase in (OUTBOUND, INBOUND):
                ant.ticks_left -= 1
                if ant.ticks_left <= 0:
                    branch = ant.branch
                    if ant.phase == OUTBOUND:
                        if deposit_out:
                            self._deposit(branch)   # arrived at food
                        ant.phase = INBOUND
                        ant.ticks_left = self.travel_time[branch]
                    else:                           # INBOUND -> arrived home
                        if deposit_in:
                            self._deposit(branch)
                        ant.phase = AT_NEST
                        ant.branch = None
                        ant.ticks_left = 0

        # keep the rolling traffic buffer bounded (only the trailing window is ever read).
        if len(self._recent_choices) > self.traffic_window:
            del self._recent_choices[:-self.traffic_window]

        # (3) evaporation.
        if self.rho > 0.0:
            decay = 1.0 - self.rho
            self.pheromone[SHORT] *= decay
            self.pheromone[LONG] *= decay

        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_ticks: int = 2000, *, measure_last: int = 200) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_ticks`` colony ticks; return the run summary.

        ``measure_last`` is the trailing window over which the steady-state short-path
        fraction is averaged. Returns the steady short fraction, the final short fraction,
        the winning branch (by final fraction), and the full per-tick series.
        """
        if measure_last <= 0 or measure_last > n_ticks + 1:
            raise ValueError(
                f"measure_last must be in [1, n_ticks+1] (got {measure_last}, "
                f"n_ticks={n_ticks})")
        self.reporter.collect(self)              # t=0 baseline
        for _ in range(n_ticks):
            self.step()
        frac_series = self.reporter.series("short_fraction")
        phi_s_series = self.reporter.series("phi_short")
        phi_l_series = self.reporter.series("phi_long")
        steady = _tail_mean(frac_series, window=measure_last)
        final = frac_series[-1]
        # which branch the colony settled on (by the steady short-path fraction).
        winner = SHORT if steady >= 0.5 else LONG
        return {
            "n_ants": self.n_ants,
            "len_short": self.lengths[SHORT],
            "len_long": self.lengths[LONG],
            "k": self.k,
            "alpha": self.alpha,
            "q": self.q,
            "rho": self.rho,
            "speed": self.speed,
            "deposit_on": self.deposit_on,
            "inject_per_tick": self.inject_per_tick,
            "travel_time_short": self.travel_time[SHORT],
            "travel_time_long": self.travel_time[LONG],
            "seed": self.seed_value,
            "n_ticks": n_ticks,
            "measure_last": measure_last,
            "steady_short_fraction": steady,
            "final_short_fraction": final,
            "winner": "short" if winner == SHORT else "long",
            "final_phi_short": phi_s_series[-1],
            "final_phi_long": phi_l_series[-1],
            "short_fraction_series": frac_series,
            "phi_short_series": phi_s_series,
            "phi_long_series": phi_l_series,
        }


# -- summary helpers ----------------------------------------------------------

def _tail_mean(series: Sequence[float], *, window: int = 200) -> float:
    """Mean of the trailing ``window`` of a series (or the whole series if shorter)."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(n_ants: int = 64, *, len_short: float = 1.0, len_long: float = 2.0,
               k: float = 20.0, alpha: float = 2.0, q: float = 1.0, rho: float = 0.02,
               speed: float = 10.0, deposit_on: str = "both", inject_per_tick: int = 2,
               traffic_window: int = 200, seed: int = 0, n_ticks: int = 2000,
               measure_last: int = 200) -> Dict[str, Any]:
    """One double-bridge run at a given (lengths, constants, seed)."""
    return AntColonyModel(
        n_ants, len_short=len_short, len_long=len_long, k=k, alpha=alpha, q=q, rho=rho,
        speed=speed, deposit_on=deposit_on, inject_per_tick=inject_per_tick,
        traffic_window=traffic_window, seed=seed,
    ).run(n_ticks, measure_last=measure_last)


def run_many_seeds(n_ants: int = 64, *, len_short: float = 1.0, len_long: float = 2.0,
                   k: float = 20.0, alpha: float = 2.0, q: float = 1.0, rho: float = 0.02,
                   speed: float = 10.0, deposit_on: str = "both", inject_per_tick: int = 2,
                   traffic_window: int = 200, n_seeds: int = 5, seed_base: int = 0,
                   n_ticks: int = 2000, measure_last: int = 200) -> Dict[str, Any]:
    """Run ``n_seeds`` double-bridge runs (seed ``seed_base + i``) at fixed parameters and
    summarise the steady short-path fraction across seeds.

    Returns the per-seed steady + final short fractions, the per-seed winning branch, their
    mean / spread, the count of seeds whose steady fraction clears 0.8 (and, for the
    symmetric arm, whose final fraction clears 0.8 on a single path either way), and one
    representative set of trajectories (first seed) for plotting/inspection.
    """
    runs = [run_single(n_ants, len_short=len_short, len_long=len_long, k=k, alpha=alpha,
                        q=q, rho=rho, speed=speed, deposit_on=deposit_on,
                        inject_per_tick=inject_per_tick, traffic_window=traffic_window,
                        seed=seed_base + i, n_ticks=n_ticks, measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_steady = [rr["steady_short_fraction"] for rr in runs]
    per_seed_final = [rr["final_short_fraction"] for rr in runs]
    per_seed_winner = [rr["winner"] for rr in runs]
    mean_steady = sum(per_seed_steady) / n_seeds
    var_steady = sum((s - mean_steady) ** 2 for s in per_seed_steady) / n_seeds
    # how many seeds put >0.8 traffic on the SHORT branch at steady state (P1).
    n_short_dominant = sum(1 for s in per_seed_steady if s > 0.8)
    # how many seeds broke symmetry onto SOME single branch (final frac >0.8 OR <0.2) (P2).
    n_symmetry_broken = sum(1 for f in per_seed_final if f > 0.8 or f < 0.2)
    n_winner_short = sum(1 for w in per_seed_winner if w == "short")
    n_winner_long = n_seeds - n_winner_short
    return {
        "n_ants": n_ants,
        "len_short": len_short,
        "len_long": len_long,
        "k": k,
        "alpha": alpha,
        "q": q,
        "rho": rho,
        "speed": speed,
        "deposit_on": deposit_on,
        "inject_per_tick": inject_per_tick,
        "traffic_window": traffic_window,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "n_ticks": n_ticks,
        "measure_last": measure_last,
        "per_seed_steady": per_seed_steady,
        "per_seed_final": per_seed_final,
        "per_seed_winner": per_seed_winner,
        "mean_steady_short_fraction": mean_steady,
        "var_steady_short_fraction": var_steady,
        "std_steady_short_fraction": var_steady ** 0.5,
        "min_steady_short_fraction": min(per_seed_steady),
        "max_steady_short_fraction": max(per_seed_steady),
        "n_short_dominant": n_short_dominant,
        "frac_short_dominant": n_short_dominant / n_seeds,
        "n_symmetry_broken": n_symmetry_broken,
        "frac_symmetry_broken": n_symmetry_broken / n_seeds,
        "n_winner_short": n_winner_short,
        "n_winner_long": n_winner_long,
        # one representative set of trajectories (first seed) for plotting/inspection.
        "example_short_fraction_series": runs[0]["short_fraction_series"],
        "example_phi_short_series": runs[0]["phi_short_series"],
        "example_phi_long_series": runs[0]["phi_long_series"],
    }
