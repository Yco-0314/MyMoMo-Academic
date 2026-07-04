"""Agent Lotka-Volterra predator-prey — a faithful agent-based reproduction.

Source: Lotka, A.J. (1925) *Elements of Physical Biology* (Williams & Wilkins);
Volterra, V. (1926) "Fluctuations in the abundance of a species considered
mathematically", Nature 118:558-560. The classic agent-based realisation is the
NetLogo "Wolf Sheep Predation" model (Wilensky 1997) — this module reproduces that
genuinely individual-based formulation rather than integrating the LV ODEs.

The continuous Lotka-Volterra ODEs are neutrally stable: their amplitude is set by
the initial condition and any perturbation rides on forever. An agent model is
NOT that — it is a stochastic, discrete, spatial system that is famously
EXTINCTION-PRONE (demographic noise can drive either species to zero). To give the
system the carrying-capacity term that lets a limit cycle SUSTAIN rather than spiral
out, prey graze on a regrowing GRASS resource (a finite per-cell food supply), exactly
as in the NetLogo wolf-sheep-grass variant. This is the documented "carrying-capacity"
choice the task calls for; without it the prey would grow without bound between predator
crashes and the discrete dynamics would not settle onto a sustained cycle.

Rules (faithful to the NetLogo wolf-sheep-grass model):

  Grid (the world):
    * An L x L grid, TOROIDAL (wraps both directions). L=100 by default.
    * Each cell carries GRASS that is either grown (edible) or eaten. An eaten cell
      regrows after a fixed countdown (``grass_regrow`` ticks). Grass is the prey's
      food and the system's carrying-capacity term.

  Prey (``PreyAgent`` — the "sheep"):
    Each tick, in scheduled order:
        1. MOVE to a uniformly-random one of the 8 (Moore) neighbour cells; pay
           ``move_cost`` energy.
        2. EAT: if its cell's grass is grown, eat it (cell -> eaten + countdown reset)
           and gain ``prey_gain`` energy.
        3. DIE if energy < 0.
        4. REPRODUCE with probability ``prey_reproduce`` (independent per tick): the
           parent SPLITS its energy in half and an offspring is spawned on the parent's
           cell carrying the other half (the NetLogo "hatch" rule).

  Predators (``PredatorAgent`` — the "wolves"):
    Each tick, in scheduled order:
        1. MOVE to a uniformly-random Moore neighbour; pay ``move_cost`` energy.
        2. EAT: if a living prey is on its cell, eat ONE (that prey dies) and gain
           ``pred_gain`` energy.
        3. DIE if energy < 0.
        4. REPRODUCE with probability ``pred_reproduce``: split energy, spawn an
           offspring on the cell with half the energy.

  Outcome = the prey and predator POPULATION time series. The agent system produces
  coupled oscillations in which the predator population peaks AFTER the prey population
  (predator lags prey) — the Lotka-Volterra signature — for the seeds in which neither
  species goes extinct.

Built on the neutral platform (``abm_auto._platform``): prey and predators are
``Agent`` subclasses driven by an ``AgentSet`` scheduler; the model owns the grass
grid + the birth/death bookkeeping and a ``DataCollector`` for the two population
series. Deterministic given a seed (one seeded RNG chain on the model).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

Cell = Tuple[int, int]

# The 8 Moore-neighbourhood offsets (drow, dcol); movement picks one uniformly.
_MOORE: Tuple[Cell, ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 1),
    (1, -1), (1, 0), (1, 1),
)


# -- agents -------------------------------------------------------------------

class _Mover(Agent):
    """Shared move/death/reproduce machinery for both species. Carries a grid
    ``cell`` and an ``energy``; ``alive`` flags removal."""

    species: str = "?"

    def __init__(self, agent_id: int, model: "LotkaVolterraModel", *, cell: Cell,
                 energy: float) -> None:
        super().__init__(agent_id, model)
        self.cell = cell
        self.energy = float(energy)
        self.alive = True

    def move(self) -> None:
        """Step to a uniformly-random Moore neighbour (toroidal) and pay move cost."""
        m = self.model
        dr, dc = m.rng.choice(_MOORE)
        r, c = self.cell
        self.cell = ((r + dr) % m.L, (c + dc) % m.L)
        self.energy -= m.move_cost


class PreyAgent(_Mover):
    """A prey ("sheep"): moves, eats grown grass, reproduces, dies at energy<0."""

    species = "prey"

    def step(self) -> None:
        if not self.alive:
            return
        m = self.model
        self.move()
        m.register_prey_cell(self)           # so predators can find prey by cell
        if m.eat_grass(self.cell):
            self.energy += m.prey_gain
        if self.energy < 0:
            m.kill(self)
            return
        if m.rng.random() < m.prey_reproduce:
            m.hatch(self)


class PredatorAgent(_Mover):
    """A predator ("wolf"): moves, eats a prey on its cell, reproduces, dies."""

    species = "predator"

    def step(self) -> None:
        if not self.alive:
            return
        m = self.model
        self.move()
        prey = m.prey_on_cell(self.cell)
        if prey is not None:
            m.kill(prey)
            self.energy += m.pred_gain
        if self.energy < 0:
            m.kill(self)
            return
        if m.rng.random() < m.pred_reproduce:
            m.hatch(self)


# -- model --------------------------------------------------------------------

class LotkaVolterraModel(AgentModel):
    """Agent-based wolf-sheep-grass Lotka-Volterra dynamics on a toroidal grid.

    One tick: every living agent (prey + predators interleaved in a single random
    order) takes its turn (move -> eat -> death -> reproduce), THEN the grass
    countdown advances by one for every eaten cell. The two population series are
    collected per tick. Deterministic given the seed.
    """

    def __init__(self, *, L: int = 100,
                 n_prey: int = 500, n_pred: int = 100,
                 prey_gain: float = 5.0, pred_gain: float = 25.0,
                 prey_reproduce: float = 0.03, pred_reproduce: float = 0.04,
                 move_cost: float = 1.0,
                 grass_regrow: int = 40,
                 init_energy_prey: Tuple[float, float] = (0.0, 10.0),
                 init_energy_pred: Tuple[float, float] = (0.0, 50.0),
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="random_order")
        self.L = L
        self.prey_gain = prey_gain
        self.pred_gain = pred_gain
        self.prey_reproduce = prey_reproduce
        self.pred_reproduce = pred_reproduce
        self.move_cost = move_cost
        self.grass_regrow = grass_regrow
        self.init_energy_prey = init_energy_prey
        self.init_energy_pred = init_energy_pred

        # Grass: grown[r][c] True iff edible; countdown[r][c] ticks-until-regrow for
        # eaten cells. Start with grass grown everywhere on a RANDOM regrow phase so
        # the landscape is not synchronised. We model grass as a boolean + countdown.
        self.grass_grown: List[List[bool]] = [[True] * L for _ in range(L)]
        self.grass_countdown: List[List[int]] = [[0] * L for _ in range(L)]
        # randomise initial grass state so half the cells start eaten (mid-regrow),
        # matching NetLogo's randomised initial grass clocks (carrying capacity is the
        # same in expectation; this just de-synchronises the resource).
        for r in range(L):
            for c in range(L):
                if self.rng.random() < 0.5:
                    self.grass_grown[r][c] = False
                    self.grass_countdown[r][c] = self.rng.randint(1, grass_regrow)

        # prey occupancy index: cell -> list of living prey on it (for predator lookup).
        self._prey_by_cell: Dict[Cell, List[PreyAgent]] = {}

        self._next_id = 0
        self.living: List[_Mover] = []
        plo, phi = init_energy_prey
        wlo, whi = init_energy_pred
        for _ in range(n_prey):
            self._spawn(PreyAgent, self._rand_cell(), self.rng.uniform(plo, phi))
        for _ in range(n_pred):
            self._spawn(PredatorAgent, self._rand_cell(), self.rng.uniform(wlo, whi))

        self.n_prey_initial = n_prey
        self.n_pred_initial = n_pred

        self.reporter = DataCollector({
            "prey": lambda m: m.prey_count(),
            "predators": lambda m: m.pred_count(),
            "grass": lambda m: m.grass_count(),
        })

    # -- construction helpers --
    def _rand_cell(self) -> Cell:
        return (self.rng.randrange(self.L), self.rng.randrange(self.L))

    def _spawn(self, cls, cell: Cell, energy: float) -> _Mover:
        a = cls(self._next_id, self, cell=cell, energy=energy)
        self._next_id += 1
        self.living.append(a)
        self.add_agent(a)
        if isinstance(a, PreyAgent):
            self._prey_by_cell.setdefault(cell, []).append(a)
        return a

    # -- prey occupancy index (rebuilt per move so predators find current prey) --
    def register_prey_cell(self, prey: PreyAgent) -> None:
        """Re-index a prey after it moves (remove from its stale bucket is lazy:
        ``prey_on_cell`` filters dead/displaced prey, so we only add here)."""
        self._prey_by_cell.setdefault(prey.cell, []).append(prey)

    def prey_on_cell(self, cell: Cell) -> Optional[PreyAgent]:
        """Return one living prey currently standing on ``cell`` (or None). Filters
        out stale index entries (prey that died or moved away since indexing)."""
        bucket = self._prey_by_cell.get(cell)
        if not bucket:
            return None
        kept: List[PreyAgent] = []
        found: Optional[PreyAgent] = None
        for p in bucket:
            if p.alive and p.cell == cell:
                if found is None:
                    found = p
                else:
                    kept.append(p)
            # dead/moved prey are dropped from this bucket
        # leave the remaining (un-eaten) prey in the index; the eaten one (found)
        # will be marked dead by the caller so a later lookup skips it.
        if found is not None:
            kept_with_found = [found] + kept
        else:
            kept_with_found = kept
        self._prey_by_cell[cell] = kept_with_found
        return found

    # -- grass --
    def eat_grass(self, cell: Cell) -> bool:
        """If ``cell`` has grown grass, eat it (start its regrow countdown) and
        return True; else return False."""
        r, c = cell
        if self.grass_grown[r][c]:
            self.grass_grown[r][c] = False
            self.grass_countdown[r][c] = self.grass_regrow
            return True
        return False

    def regrow_grass(self) -> None:
        """Advance every eaten cell's countdown by one; regrow on hitting zero."""
        gc = self.grass_countdown
        gg = self.grass_grown
        L = self.L
        for r in range(L):
            cd_row = gc[r]
            gg_row = gg[r]
            for c in range(L):
                if not gg_row[c]:
                    cd_row[c] -= 1
                    if cd_row[c] <= 0:
                        gg_row[c] = True
                        cd_row[c] = 0

    # -- birth / death --
    def hatch(self, parent: _Mover) -> None:
        """Reproduce: parent splits its energy; offspring of the same species spawns
        on the parent's cell with half the energy (the NetLogo hatch rule)."""
        parent.energy /= 2.0
        cls = type(parent)
        self._spawn(cls, parent.cell, parent.energy)

    def kill(self, agent: _Mover) -> None:
        agent.alive = False

    # -- metrics --
    def prey_count(self) -> int:
        return sum(1 for a in self.living if a.alive and a.species == "prey")

    def pred_count(self) -> int:
        return sum(1 for a in self.living if a.alive and a.species == "predator")

    def grass_count(self) -> int:
        return sum(1 for row in self.grass_grown for g in row if g)

    # -- tick --
    def step(self) -> None:
        """One tick: all living agents act in a single random order (prey + predators
        interleaved), then grass regrows, then the dead are pruned and the prey index
        rebuilt for the next tick."""
        # snapshot the schedule order; births this tick act NEXT tick (they are added
        # to self.living but not to this tick's ordered snapshot).
        for agent in self.agents.ordered():
            if agent.alive:
                agent.step()
        self.regrow_grass()
        # prune the dead; rebuild scheduler + prey index from the survivors.
        self.living = [a for a in self.living if a.alive]
        self.agents._agents = list(self.living)
        self._prey_by_cell = {}
        for a in self.living:
            if isinstance(a, PreyAgent):
                self._prey_by_cell.setdefault(a.cell, []).append(a)
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_steps: int) -> Dict[str, Any]:  # type: ignore[override]
        """Advance up to ``n_steps`` ticks (stop early iff BOTH species are extinct);
        return a summary dict with config + the prey/predator/grass series."""
        self.reporter.collect(self)               # t=0 baseline
        for _ in range(n_steps):
            if self.prey_count() == 0 and self.pred_count() == 0:
                break
            self.step()
        prey_series = self.reporter.series("prey")
        pred_series = self.reporter.series("predators")
        grass_series = self.reporter.series("grass")
        return {
            "L": self.L,
            "n_prey_initial": self.n_prey_initial,
            "n_pred_initial": self.n_pred_initial,
            "prey_gain": self.prey_gain,
            "pred_gain": self.pred_gain,
            "prey_reproduce": self.prey_reproduce,
            "pred_reproduce": self.pred_reproduce,
            "move_cost": self.move_cost,
            "grass_regrow": self.grass_regrow,
            "steps": self.t,
            "prey_series": prey_series,
            "pred_series": pred_series,
            "grass_series": grass_series,
            "final_prey": prey_series[-1],
            "final_pred": pred_series[-1],
        }


# -- analysis helpers ---------------------------------------------------------

def count_peaks(series: Sequence[float], *, min_prominence: float = 0.0,
                min_height_frac: float = 0.0) -> int:
    """Count local maxima in ``series`` (a peak = strictly higher than both
    immediate neighbours, with equal-plateau handling).

    A point i (1 <= i <= n-2) is a peak iff there exist neighbours j<i, k>i such
    that series[j] < series[i], series[k] < series[i], and series is non-increasing
    between... — we use a simpler robust rule: scan for up-then-down transitions,
    treating flat plateaus as a single candidate.

    ``min_height_frac``: a peak must exceed this fraction of the series max to count
    (filters tiny ripples near zero). ``min_prominence``: a peak must rise at least
    this much above the lower of the two flanking valleys to count.
    """
    xs = [float(v) for v in series]
    n = len(xs)
    if n < 3:
        return 0
    hi = max(xs)
    height_floor = min_height_frac * hi
    # find indices of strict local maxima, collapsing plateaus to their first index.
    peaks: List[int] = []
    i = 1
    while i < n - 1:
        if xs[i] > xs[i - 1]:
            # climbed; find end of a (possibly flat) plateau at this level
            j = i
            while j < n - 1 and xs[j + 1] == xs[i]:
                j += 1
            if j < n - 1 and xs[j + 1] < xs[i]:
                peaks.append(i)
                i = j + 1
                continue
            i = j + 1
        else:
            i += 1
    if min_prominence <= 0.0 and height_floor <= 0.0:
        return len(peaks)
    # prominence/height filter
    kept = 0
    for p in peaks:
        if xs[p] < height_floor:
            continue
        # left valley
        lv = min(xs[:p]) if p > 0 else xs[p]
        rv = min(xs[p + 1:]) if p < n - 1 else xs[p]
        prom = xs[p] - max(lv, rv)
        if prom >= min_prominence:
            kept += 1
    return kept


def moving_average(series: Sequence[float], window: int) -> List[float]:
    """Centred moving average with a ``window``-tick box filter (edges shrink the
    window). Smooths out the tick-level demographic NOISE so the macroscopic
    Lotka-Volterra CYCLE is what the peak-count and cross-correlation see, rather
    than every one-tick wiggle. ``window<=1`` is a no-op (returns a copy)."""
    xs = [float(v) for v in series]
    n = len(xs)
    if window <= 1 or n == 0:
        return xs
    half = window // 2
    out: List[float] = []
    for i in range(n):
        a = max(0, i - half)
        b = min(n, i + half + 1)
        out.append(sum(xs[a:b]) / (b - a))
    return out


def cross_correlation(x: Sequence[float], y: Sequence[float],
                      max_lag: int) -> List[Tuple[int, float]]:
    """Normalised cross-correlation of ``x`` and ``y`` over lags in [-max_lag, max_lag].

    Convention: lag k correlates x[t] with y[t+k]. A POSITIVE peak lag therefore
    means y (the predator) follows x (the prey) by k ticks. Both series are
    mean-centred and the result is normalised by the product of their standard
    deviations so the values lie in roughly [-1, 1]. Returns [(lag, corr), ...].
    """
    xs = [float(v) for v in x]
    ys = [float(v) for v in y]
    n = min(len(xs), len(ys))
    xs, ys = xs[:n], ys[:n]
    mx = sum(xs) / n
    my = sum(ys) / n
    dx = [v - mx for v in xs]
    dy = [v - my for v in ys]
    sx = (sum(v * v for v in dx)) ** 0.5
    sy = (sum(v * v for v in dy)) ** 0.5
    denom = sx * sy
    out: List[Tuple[int, float]] = []
    for k in range(-max_lag, max_lag + 1):
        s = 0.0
        # sum over t where both t and t+k are valid
        if k >= 0:
            for t in range(0, n - k):
                s += dx[t] * dy[t + k]
        else:
            for t in range(-k, n):
                s += dx[t] * dy[t + k]
        out.append((k, s / denom if denom > 0 else 0.0))
    return out


def best_positive_lag(x: Sequence[float], y: Sequence[float],
                      max_lag: int) -> Tuple[int, float]:
    """Lag (and correlation) at which the cross-correlation is MAXIMISED.

    Returns (argmax_lag, corr_at_that_lag). A positive lag means y lags x.
    """
    cc = cross_correlation(x, y, max_lag)
    return max(cc, key=lambda kv: kv[1])


# -- multi-seed harness -------------------------------------------------------

def run_single(*, L: int = 100, n_prey: int = 500, n_pred: int = 100,
               prey_gain: float = 5.0, pred_gain: float = 25.0,
               prey_reproduce: float = 0.03, pred_reproduce: float = 0.04,
               move_cost: float = 1.0, grass_regrow: int = 40,
               n_steps: int = 1000, seed: int = 0) -> Dict[str, Any]:
    """One full agent Lotka-Volterra run for a given seed."""
    model = LotkaVolterraModel(
        L=L, n_prey=n_prey, n_pred=n_pred, prey_gain=prey_gain, pred_gain=pred_gain,
        prey_reproduce=prey_reproduce, pred_reproduce=pred_reproduce,
        move_cost=move_cost, grass_regrow=grass_regrow, seed=seed,
    )
    res = model.run(n_steps)
    res["seed"] = seed
    return res


def _survived(res: Dict[str, Any]) -> bool:
    """A seed 'survived' iff NEITHER species went extinct over the whole run, i.e.
    every tick has prey>0 and predators>0 (no zero anywhere in the series)."""
    return min(res["prey_series"]) > 0 and min(res["pred_series"]) > 0


def analyse_seed(res: Dict[str, Any], *, max_lag: int = 200,
                 smooth_window: int = 25,
                 peak_prominence_frac: float = 0.10) -> Dict[str, Any]:
    """Per-seed analysis on the SMOOTHED population series.

    The raw per-tick series carry heavy demographic noise (every tick wiggles), so
    the macroscopic LV cycle is measured on a ``smooth_window``-tick moving average.
    A peak must rise at least ``peak_prominence_frac`` of the (smoothed) series'
    peak-to-trough amplitude above its flanking valleys to count, which removes
    residual ripples while keeping the real cycles. The cross-correlation lag is
    taken on the same smoothed series; a POSITIVE peak lag means the predator follows
    the prey. Survival is judged on the RAW series (a true zero is extinction)."""
    prey_raw = res["prey_series"]
    pred_raw = res["pred_series"]
    n = len(prey_raw)
    survived = _survived(res)
    prey = moving_average(prey_raw, smooth_window)
    pred = moving_average(pred_raw, smooth_window)
    amp_prey = max(prey) - min(prey)
    amp_pred = max(pred) - min(pred)
    prom_prey = peak_prominence_frac * amp_prey
    prom_pred = peak_prominence_frac * amp_pred
    prey_peaks = count_peaks(prey, min_prominence=prom_prey)
    pred_peaks = count_peaks(pred, min_prominence=prom_pred)
    # last-third persistence: peaks within the trailing third of the SMOOTHED series.
    cut = (2 * n) // 3
    prey_peaks_last = count_peaks(prey[cut:], min_prominence=prom_prey)
    pred_peaks_last = count_peaks(pred[cut:], min_prominence=prom_pred)
    lag, corr = best_positive_lag(prey, pred, min(max_lag, n - 1))
    return {
        "seed": res["seed"],
        "survived": survived,
        "steps": res["steps"],
        "final_prey": res["final_prey"],
        "final_pred": res["final_pred"],
        "min_prey": min(prey_raw),
        "min_pred": min(pred_raw),
        "max_prey": max(prey_raw),
        "max_pred": max(pred_raw),
        "amp_prey_smoothed": round(amp_prey, 3),
        "amp_pred_smoothed": round(amp_pred, 3),
        "prey_peaks": prey_peaks,
        "pred_peaks": pred_peaks,
        "prey_peaks_last_third": prey_peaks_last,
        "pred_peaks_last_third": pred_peaks_last,
        "best_lag": lag,
        "best_lag_corr": round(corr, 4),
    }


def run_many_seeds(seeds: Sequence[int], *, L: int = 100, n_prey: int = 500,
                   n_pred: int = 100, prey_gain: float = 5.0, pred_gain: float = 25.0,
                   prey_reproduce: float = 0.03, pred_reproduce: float = 0.04,
                   move_cost: float = 1.0, grass_regrow: int = 40,
                   n_steps: int = 1000, max_lag: int = 200,
                   smooth_window: int = 25,
                   peak_prominence_frac: float = 0.10) -> Dict[str, Any]:
    """Run one simulation per seed; return per-seed rows + the series + cross-seed
    summary (survival fraction, peak counts, cross-correlation lags).

    Only the SURVIVING seeds (neither species extinct) feed the lag (P2) and the
    last-third persistence (P3) aggregates — the locked clauses specify this.
    """
    rows: List[Dict[str, Any]] = []
    analyses: List[Dict[str, Any]] = []
    for s in seeds:
        res = run_single(
            L=L, n_prey=n_prey, n_pred=n_pred, prey_gain=prey_gain,
            pred_gain=pred_gain, prey_reproduce=prey_reproduce,
            pred_reproduce=pred_reproduce, move_cost=move_cost,
            grass_regrow=grass_regrow, n_steps=n_steps, seed=s,
        )
        rows.append(res)
        analyses.append(analyse_seed(res, max_lag=max_lag,
                                     smooth_window=smooth_window,
                                     peak_prominence_frac=peak_prominence_frac))
    n = len(analyses)
    survived = [a for a in analyses if a["survived"]]
    n_surv = len(survived)
    survival_fraction = n_surv / n if n else 0.0
    # P1: both populations >= 2 peaks AND neither extinct, per seed.
    p1_seeds = [a for a in analyses
                if a["survived"] and a["prey_peaks"] >= 2 and a["pred_peaks"] >= 2]
    p1_fraction = len(p1_seeds) / n if n else 0.0
    # P2 across surviving seeds: positive best lag.
    pos_lag = [a for a in survived if a["best_lag"] > 0]
    p2_positive_fraction = len(pos_lag) / n_surv if n_surv else 0.0
    median_best_lag = (sorted(a["best_lag"] for a in survived)[n_surv // 2]
                       if n_surv else 0)
    # P3 across surviving seeds: peaks persist into the last third (both species >=1).
    p3_seeds = [a for a in survived
                if a["prey_peaks_last_third"] >= 1 and a["pred_peaks_last_third"] >= 1]
    p3_fraction = len(p3_seeds) / n_surv if n_surv else 0.0
    return {
        "seeds": list(seeds),
        "config": {
            "L": L, "n_prey": n_prey, "n_pred": n_pred,
            "prey_gain": prey_gain, "pred_gain": pred_gain,
            "prey_reproduce": prey_reproduce, "pred_reproduce": pred_reproduce,
            "move_cost": move_cost, "grass_regrow": grass_regrow,
            "n_steps": n_steps, "max_lag": max_lag,
            "smooth_window": smooth_window,
            "peak_prominence_frac": peak_prominence_frac,
        },
        "rows": rows,
        "analyses": analyses,
        "n_seeds": n,
        "n_survived": n_surv,
        "survival_fraction": survival_fraction,
        "p1_both_oscillate_fraction": p1_fraction,
        "p2_positive_lag_fraction": p2_positive_fraction,
        "median_best_lag_surviving": median_best_lag,
        "p3_last_third_fraction": p3_fraction,
    }
