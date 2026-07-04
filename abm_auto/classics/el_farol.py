"""El Farol Bar problem (Arthur 1994) — a faithful agent-based reproduction.

Source: Arthur, W.B. (1994) "Inductive Reasoning and Bounded Rationality",
American Economic Review 84(2):406-411 (the "El Farol" paper).
Open: https://www.santafe.edu/research/results/working-papers/inductive-reasoning-and-bounded-rationality

The set-up (verified against the paper):
  * N people (Arthur: 100) each independently decide every week whether to go to
    the El Farol bar. The bar is enjoyable only if it is not too crowded; Arthur
    fixes the comfort CAPACITY at 60. If you expect MORE than 60 to attend you
    stay home; if you expect FEWER than 60 you go. There is no communication and
    no shared model — each agent reasons INDUCTIVELY from the public attendance
    history.
  * Each agent is given, once, a small fixed set of ``k`` PREDICTORS drawn from a
    common repertoire. A predictor maps the recent attendance history to a forecast
    of THIS week's attendance (e.g. "same as last week", "mirror image around
    100−x", "rounded average of the last d weeks", a fixed constant, a linear
    trend). The predictors are the agent's hypotheses; they are NOT changed.
  * Each week, every agent:
      1. Evaluates each of its predictors on the available history and picks its
         currently most ACCURATE one (the "active" predictor — lowest recent error).
      2. Forecasts next attendance with that active predictor and GOES iff the
         forecast is < capacity (60), else stays home.
      3. The realized attendance (how many actually went) is tallied and appended
         to the public history.
      4. Every predictor of every agent is re-SCORED against the just-revealed
         attendance (its squared/abs error is folded into a recent-accuracy score),
         so next week a different predictor may become active. This is Arthur's
         "the agents' active predictors co-evolve with the attendance they create."

Arthur's headline result: with no coordination and no equilibrium model, mean
attendance SELF-ORGANIZES to fluctuate around the capacity 60 (his runs settle to a
long-run mean of ~56-60); the "forecasting ecology" keeps roughly 60% going. That
emergent near-capacity mean is the LOCKED metric here.

Determinism / locality: the only public object an agent reads is the shared
attendance history (a sequence of past weekly counts) — no agent sees another's
predictor or decision. One seeded RNG chain draws every agent's predictor set and
the random initial history, so the whole run replays bit-for-bit from a seed.

Built on the neutral platform (``abm_auto._platform``): each person is a
``BarAgent`` carrying its fixed predictor set + per-predictor error scores;
``ElFarolModel`` drives the weeks over the ``AgentSet`` roster and records (via a
``DataCollector``) the per-week attendance so the post-transient mean/std can be
computed.
"""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Predictor repertoire -----------------------------------------------------
#
# A predictor is a pure function ``history -> forecast`` over the attendance
# history (a list where ``history[-1]`` is last week). Each carries a short label
# so a run's predictor ecology is inspectable. Forecasts are clamped to [0, N] by
# the model when scored; the raw functions may return out-of-range values (e.g. a
# trend extrapolation), which is faithful — a wild predictor simply scores badly.

Predictor = Tuple[str, Callable[[Sequence[int]], float]]


def _last(history: Sequence[int]) -> float:
    """Same as last week."""
    return float(history[-1])


def _mirror(n: int) -> Callable[[Sequence[int]], float]:
    """Mirror image of last week around N/2: forecast = N - last. (Arthur's
    'the mirror image around 50' for N=100.)"""
    def f(history: Sequence[int]) -> float:
        return float(n - history[-1])
    return f


def _average(d: int) -> Callable[[Sequence[int]], float]:
    """(Rounded) average of the last ``d`` weeks."""
    def f(history: Sequence[int]) -> float:
        window = history[-d:]
        return sum(window) / len(window)
    return f


def _fixed(value: float) -> Callable[[Sequence[int]], float]:
    """A fixed constant forecast (a 'stubborn' belief about the level)."""
    def f(history: Sequence[int]) -> float:
        return float(value)
    return f


def _trend(d: int) -> Callable[[Sequence[int]], float]:
    """Linear trend: extrapolate the last-``d``-week slope one step forward.
    forecast = last + (last - history[-d]) / (d-1)  (a simple momentum/cycle term)."""
    def f(history: Sequence[int]) -> float:
        if len(history) < d:
            return float(history[-1])
        first = history[-d]
        last = history[-1]
        slope = (last - first) / (d - 1)
        return last + slope
    return f


def _weighted_last_two(history: Sequence[int]) -> float:
    """Weighted recent: 2*last - second-last (a sharper momentum predictor)."""
    if len(history) < 2:
        return float(history[-1])
    return 2.0 * history[-1] - history[-2]


def default_repertoire(n: int = 100) -> List[Predictor]:
    """The FIXED predictor repertoire (locked before running; not tuned).

    A heterogeneous spread of inductive hypotheses in the spirit of Arthur's
    examples: persistence, mirror image, several moving averages, fixed beliefs at
    a spread of levels (including around capacity), and momentum/trend terms. Each
    agent is dealt ``k`` of these at random; the set is identical across seeds so
    only the DEAL (which predictors each agent holds) and the initial history vary.
    """
    rep: List[Predictor] = [
        ("same_as_last_week", _last),
        ("mirror_around_half", _mirror(n)),
        ("avg_last_2", _average(2)),
        ("avg_last_3", _average(3)),
        ("avg_last_4", _average(4)),
        ("avg_last_5", _average(5)),
        ("avg_last_8", _average(8)),
        ("fixed_40", _fixed(40)),
        ("fixed_50", _fixed(50)),
        ("fixed_55", _fixed(55)),
        ("fixed_60", _fixed(60)),
        ("fixed_65", _fixed(65)),
        ("trend_2", _trend(2)),
        ("trend_3", _trend(3)),
        ("trend_5", _trend(5)),
        ("weighted_last_two", _weighted_last_two),
    ]
    return rep


# -- Agent --------------------------------------------------------------------

class BarAgent(Agent):
    """One El Farol bar-goer holding ``k`` fixed predictors + their error scores.

    ``predictors`` is a list of (label, fn). ``errors`` is an exponentially-weighted
    recent SQUARED-error score per predictor (lower = more accurate). The agent's
    *active* predictor each week is the lowest-error one (ties → lowest index, i.e.
    the order it was dealt — deterministic). Each predictor's forecast is computed
    against the public history; the agent GOES iff its active predictor's forecast
    is below the capacity threshold."""

    def __init__(self, agent_id: int, model: "ElFarolModel", *,
                 predictors: List[Predictor], memory: float) -> None:
        super().__init__(agent_id, model)
        self.predictors = predictors
        self.memory = memory                       # EWMA weight on the new error
        # Start every predictor at zero accumulated error (neutral; the first few
        # weeks of scoring quickly separate them).
        self.errors: List[float] = [0.0] * len(predictors)
        self.went = False                          # decision of the latest week

    def best_predictor_index(self) -> int:
        """Index of the LOWEST-error predictor; ties broken to the LOWEST index."""
        best_i = 0
        best_err = self.errors[0]
        for i in range(1, len(self.errors)):
            if self.errors[i] < best_err:
                best_err = self.errors[i]
                best_i = i
        return best_i

    def forecast(self, history: Sequence[int]) -> float:
        """This week's attendance forecast from the currently best predictor."""
        _, fn = self.predictors[self.best_predictor_index()]
        return fn(history)

    def decide(self, history: Sequence[int], capacity: int) -> bool:
        """Decide whether to go: GO iff the active predictor forecasts < capacity."""
        self.went = self.forecast(history) < capacity
        return self.went

    def rescore(self, history: Sequence[int], realized: int) -> None:
        """Fold the just-revealed ``realized`` attendance into each predictor's
        recent-error score (EWMA of squared error). ``history`` is the history the
        predictors saw BEFORE this week (i.e. excluding ``realized``)."""
        m = self.memory
        for i, (_, fn) in enumerate(self.predictors):
            err = (fn(history) - realized) ** 2
            self.errors[i] = (1.0 - m) * self.errors[i] + m * err

    def step(self) -> None:  # pragma: no cover - El Farol ticks the whole week at once
        """A week couples all agents through the shared attendance + history, so a
        single agent's autonomous ``step`` is a no-op; the model's ``step`` (one
        full week) is the tick."""
        return None


# -- Model --------------------------------------------------------------------

class ElFarolModel(AgentModel):
    """Drives the El Farol bar for a fixed number of weeks.

    Construct with ``n`` people, comfort ``capacity``, predictors-per-agent ``k``,
    a fixed predictor ``repertoire`` (defaults to ``default_repertoire``), and a
    seed. ``run`` plays ``transient + weeks`` weeks, records per-week attendance,
    and returns a summary including the post-transient mean and std (the LOCKED
    metric is the post-transient MEAN attendance)."""

    def __init__(self, n: int = 100, *, capacity: int = 60, k: int = 6,
                 memory: float = 0.30, history_len: int = 12, seed: int = 0,
                 weeks: int = 200, transient: int = 100,
                 repertoire: Optional[List[Predictor]] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.seed_value = seed
        self.n = n
        self.capacity = capacity
        self.k = k
        self.memory = memory
        self.history_len = history_len
        self.weeks = weeks
        self.transient = transient
        self.repertoire = repertoire if repertoire is not None else default_repertoire(n)
        if k > len(self.repertoire):
            raise ValueError(
                f"k={k} predictors requested but repertoire has only "
                f"{len(self.repertoire)}")

        # Random initial attendance history (the seed for inductive reasoning),
        # ``history_len`` weeks of plausible counts in [0, n].
        self.history: List[int] = [self.rng.randint(0, n) for _ in range(history_len)]

        # Deal each agent k distinct predictors from the shared repertoire.
        self.agent_list: List[BarAgent] = []
        for i in range(n):
            dealt = self.rng.sample(self.repertoire, k)
            agent = BarAgent(i, self, predictors=dealt, memory=memory)
            self.agent_list.append(agent)
            self.add_agent(agent)

        #: Attendance (count who went) of the week just committed.
        self.attendance = 0

        self.reporter = DataCollector({
            "attendance": lambda mdl: mdl.attendance,
        })

    # -- one El Farol week --
    def step(self) -> None:
        """One week: every agent picks its best predictor and decides via the shared
        history; realized attendance is tallied and appended; every predictor is
        re-scored against the realized attendance; the history window slides."""
        hist = self.history
        # 1+2. Each agent forecasts from its active predictor and decides to go.
        attendance = 0
        for agent in self.agent_list:
            if agent.decide(hist, self.capacity):
                attendance += 1

        # 4. Re-score EVERY predictor against the now-revealed attendance, using the
        # SAME history the agents forecast from this week (i.e. before appending).
        for agent in self.agent_list:
            agent.rescore(hist, attendance)

        # 3. Commit: append realized attendance and slide the bounded history window.
        self.history.append(attendance)
        if len(self.history) > self.history_len:
            self.history = self.history[-self.history_len:]

        self.attendance = attendance
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Play ``transient + weeks`` weeks; compute mean/std over the post-transient
        window and return the run summary."""
        total = self.transient + self.weeks
        for _ in range(total):
            self.step()
        att = self.reporter.series("attendance")
        window = att[self.transient:]
        return {
            "n": self.n,
            "capacity": self.capacity,
            "k": self.k,
            "memory": self.memory,
            "history_len": self.history_len,
            "seed": self.seed_value,
            "weeks": self.weeks,
            "transient": self.transient,
            "attendance_window": window,
            "mean_attendance": mean(window),
            "std_attendance": std(window),
        }


# -- metrics ------------------------------------------------------------------

def mean(xs: Sequence[float]) -> float:
    """Arithmetic mean of a series (0.0 for empty)."""
    return (sum(xs) / len(xs)) if xs else 0.0


def variance(xs: Sequence[float]) -> float:
    """Population variance Var(x) = E[(x-mean)^2]."""
    k = len(xs)
    if k == 0:
        return 0.0
    mu = sum(xs) / k
    return sum((x - mu) ** 2 for x in xs) / k


def std(xs: Sequence[float]) -> float:
    """Population standard deviation."""
    return variance(xs) ** 0.5


# -- run orchestration --------------------------------------------------------

def run_single(n: int = 100, *, capacity: int = 60, k: int = 6, memory: float = 0.30,
               history_len: int = 12, seed: int = 0, weeks: int = 200,
               transient: int = 100,
               repertoire: Optional[List[Predictor]] = None) -> Dict[str, Any]:
    """One El Farol run at a given (n, capacity, k, seed)."""
    return ElFarolModel(n, capacity=capacity, k=k, memory=memory,
                        history_len=history_len, seed=seed, weeks=weeks,
                        transient=transient, repertoire=repertoire).run()


def run_many_seeds(n: int = 100, *, capacity: int = 60, k: int = 6, memory: float = 0.30,
                   history_len: int = 12, n_seeds: int = 5, seed_base: int = 0,
                   weeks: int = 200, transient: int = 100,
                   repertoire: Optional[List[Predictor]] = None) -> Dict[str, Any]:
    """Run ``n_seeds`` El Farol runs (seed ``seed_base + i``) at fixed config and
    summarise the post-transient mean attendance across seeds.

    Returns the per-seed mean + std attendance, the cross-seed mean of those means
    (the LOCKED long-run level) and its spread, and an example attendance series.
    """
    runs = [run_single(n, capacity=capacity, k=k, memory=memory,
                       history_len=history_len, seed=seed_base + i, weeks=weeks,
                       transient=transient, repertoire=repertoire)
            for i in range(n_seeds)]
    per_seed_mean = [r["mean_attendance"] for r in runs]
    per_seed_std = [r["std_attendance"] for r in runs]
    return {
        "n": n,
        "capacity": capacity,
        "k": k,
        "memory": memory,
        "history_len": history_len,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "weeks": weeks,
        "transient": transient,
        "per_seed_mean": per_seed_mean,
        "per_seed_std": per_seed_std,
        "mean_attendance": mean(per_seed_mean),       # cross-seed mean of means
        "std_of_seed_means": std(per_seed_mean),      # spread of per-seed means
        "mean_std_attendance": mean(per_seed_std),    # mean within-run std (fluctuation)
        "min_seed_mean": min(per_seed_mean),
        "max_seed_mean": max(per_seed_mean),
        "example_series": runs[0]["attendance_window"],
        "runs": runs,
    }
