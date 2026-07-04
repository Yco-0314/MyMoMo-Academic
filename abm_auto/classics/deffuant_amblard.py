"""Relative-Agreement opinion dynamics with extremists (Deffuant, Amblard,
Weisbuch & Faure 2002) — a faithful agent-based reproduction.

Source: Deffuant, G., Amblard, F., Weisbuch, G., Faure, T. (2002) "How can
extremism prevail? A study based on the relative agreement interaction model",
Journal of Artificial Societies and Social Simulation 5(4):1.

This is DISTINCT from Deffuant (2000) bounded confidence (``deffuant.py``):

  * Deffuant (2000) is a CONSTANT-threshold, OPINION-ONLY model on [0, 1]: a pair
    interacts iff ``|x_i - x_j| < eps`` for a fixed global ``eps``, and both move a
    fixed fraction toward each other. Uncertainty does not exist; there are no
    extremists.
  * This 2002 model gives every agent BOTH an opinion ``x_i in [-1, 1]`` AND its own
    evolving UNCERTAINTY ``u_i`` (an opinion SEGMENT ``[x_i - u_i, x_i + u_i]``). An
    interaction updates BOTH the opinion and the uncertainty by the RELATIVE
    AGREEMENT rule, and a small population of LOW-uncertainty EXTREMISTS at the
    opinion extremes can drag the whole moderate population to one or both poles —
    single- and double-extreme attractors the plain bounded-confidence model cannot
    reach.

Rules (verified against the paper):
  * N agents; each carries opinion ``x_i in [-1, 1]`` and uncertainty ``u_i > 0``.
  * The dynamics are PAIRWISE RANDOM ENCOUNTERS over a FULLY-CONNECTED population:
    one elementary interaction draws a random ORDERED pair ``(i, j)`` — agent *i*
    (the "influencer") acts on agent *j* (the "influenced"); the update is
    ASYMMETRIC (only *j* changes).
  * Segment overlap:
        h_ij = min(x_i + u_i, x_j + u_j) - max(x_i - u_i, x_j - u_j).
  * RELATIVE AGREEMENT — the interaction fires ONLY IF ``h_ij > u_i`` (the overlap
    exceeds *i*'s own uncertainty; the influencer must be "more certain" than the
    overlap it shares). When it fires, with ``ra = h_ij / u_i - 1`` (the relative
    agreement, in (0, 1] here since ``u_i < h_ij <= 2*u_i``):
        x_j += mu * ra * (x_i - x_j)
        u_j += mu * ra * (u_i - u_j)
    Note the denominator is ``u_i`` (the INFLUENCER's uncertainty), NOT ``2*u_i``:
    a low-uncertainty, confident influencer (small ``u_i``) yields a LARGER ``ra``
    and a stronger pull, which is exactly why the low-uncertainty extremists are so
    persuasive.
  * One "iteration" (a SWEEP) is N such random ordered-pair interactions, so each
    sweep is on the order of one interaction per agent. The model runs a fixed number
    of sweeps (the 2002 study runs to a frozen attractor).

Population set-up (the paper's extremism experiment):
  * A fraction ``p_e`` of the agents are EXTREMISTS: very low uncertainty ``u_e``
    (default 0.1) and opinions pinned at the extremes (``x = +1`` or ``x = -1``).
  * The remaining moderates start with opinions ~ Uniform[-1, 1] and a common global
    uncertainty ``U``.
  * A deterministic asymmetry ``delta in [-1, 1]`` splits the extremists between the
    two poles: the number of positive extremists is ``round(p_e * N * (1 + delta) / 2)``
    and negative is ``round(p_e * N * (1 - delta) / 2)`` (delta > 0 => a + majority of
    extremists). ``delta = 0`` is the symmetric case.

Outcome metric (locked): ``y = p'_+^2 + p'_-^2`` where ``p'_+`` (``p'_-``) is the final
fraction of INITIALLY-MODERATE agents whose opinion ends near the + (-) extreme
(``|x| > x_extreme_tol``, default 0.8). ``y ~ 0`` when the moderates stay central
(central convergence), ``y ~ 0.5`` when they split roughly evenly between the two poles
(double extreme), and ``y ~ 1`` when a single pole captures essentially all of them
(single extreme).

Locality note (no global oracle): each elementary interaction reads exactly the two
paired agents' own (x, u) and updates exactly the influenced agent's (x, u). No agent
and no update ever consults a population-level statistic. The platform ``AgentSet``
holds the roster + a seeded RNG; the *pairing* is random per interaction (the 2002
"fully connected / fully mixed" encounter model). Given a seed the whole run is
reproducible.

Built on the neutral platform (``abm_auto._platform``): each agent is a
``RAAgent`` carrying its own (x, u) and a flag marking it a (fixed-role) extremist;
``RelativeAgreementModel`` drives the random ordered-pair interactions over the
``AgentSet`` roster and records (via a ``DataCollector``) the per-sweep max opinion
change and the running polarization metric y.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class RAAgent(Agent):
    """One agent: opinion ``x`` in [-1, 1] and uncertainty ``u`` > 0 (its opinion
    segment is ``[x - u, x + u]``).

    ``is_extremist`` marks the low-uncertainty agents seeded at the poles; the metric
    is graded over the INITIALLY-MODERATE agents (``is_extremist`` False), so this flag
    (a fixed role, set at construction) is retained for the readout, not for the
    dynamics — extremists interact under the very same relative-agreement rule as
    everyone else (they are simply confident and extreme, which makes them persuasive).

    In relative-agreement dynamics the unit of update is an ORDERED pair, not a single
    agent's autonomous ``step`` (an agent only changes when it happens to be drawn as
    the *influenced* member of a pair). The pair update lives on the model
    (``interact``) so the two-agent locality — read two (x, u), write the influenced
    one's (x, u) — is explicit.
    """

    def __init__(self, agent_id: int, model: "RelativeAgreementModel", *,
                 opinion: float, uncertainty: float, is_extremist: bool = False) -> None:
        super().__init__(agent_id, model)
        self.x = opinion
        self.u = uncertainty
        self.is_extremist = is_extremist
        #: opinion at construction (initially-moderate agents are graded by their FINAL
        #: opinion; this is kept only for provenance / debugging).
        self.x0 = opinion

    def step(self) -> None:  # pragma: no cover - encounter model updates pairs, not agents
        """RA updates ordered pairs drawn by the model, not single agents in roster
        order, so the per-agent ``step`` is intentionally a no-op. The model's ``step``
        (one sweep of N random ordered-pair interactions) is the tick."""
        return None


# -- Model --------------------------------------------------------------------

class RelativeAgreementModel(AgentModel):
    """Drives the Deffuant-Amblard (2002) relative-agreement dynamics with extremists.

    Construct with N, convergence rate ``mu``, the extremist fraction ``p_e`` and
    their (low) uncertainty ``u_e``, the moderate global uncertainty ``U``, the
    pole-asymmetry ``delta``, and a seed. ``run(n_sweeps)`` advances the sweeps (each
    = N random ordered-pair interactions) and returns a summary dict (final opinions,
    the polarization metric y, capture fractions, per-sweep max-move + y series).
    """

    def __init__(self, n: int = 200, *, mu: float = 0.5, p_e: float = 0.2,
                 u_e: float = 0.1, big_u: float = 0.4, delta: float = 0.0,
                 x_extreme_tol: float = 0.8, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if not (0.0 <= p_e <= 1.0):
            raise ValueError(f"need 0 <= p_e <= 1 (got {p_e})")
        if u_e <= 0.0 or big_u <= 0.0:
            raise ValueError(f"need u_e > 0 and U > 0 (got u_e={u_e}, U={big_u})")
        if not (-1.0 <= delta <= 1.0):
            raise ValueError(f"need -1 <= delta <= 1 (got {delta})")
        self.seed_value = seed
        self.n = n
        self.mu = float(mu)
        self.p_e = float(p_e)
        self.u_e = float(u_e)
        self.big_u = float(big_u)
        self.delta = float(delta)
        self.x_extreme_tol = float(x_extreme_tol)

        #: Largest single opinion change committed in the sweep just run (per-sweep
        #: series + a convergence signal for inspection).
        self._sweep_max_move = float("inf")

        # -- seed the population --------------------------------------------------
        # Total extremists, split between the two poles by delta:
        #   n_+ = round(p_e * N * (1 + delta) / 2), n_- = round(p_e * N * (1 - delta) / 2).
        n_extreme_total = int(round(self.p_e * n))
        n_pos = int(round(n_extreme_total * (1.0 + self.delta) / 2.0))
        n_pos = max(0, min(n_extreme_total, n_pos))
        n_neg = n_extreme_total - n_pos
        self.n_pos_extreme = n_pos
        self.n_neg_extreme = n_neg
        self.n_extreme = n_extreme_total
        self.n_moderate = n - n_extreme_total

        self.agent_list: List[RAAgent] = []
        aid = 0
        # Positive extremists: x = +1, u = u_e.
        for _ in range(n_pos):
            a = RAAgent(aid, self, opinion=1.0, uncertainty=self.u_e, is_extremist=True)
            self.agent_list.append(a)
            self.add_agent(a)
            aid += 1
        # Negative extremists: x = -1, u = u_e.
        for _ in range(n_neg):
            a = RAAgent(aid, self, opinion=-1.0, uncertainty=self.u_e, is_extremist=True)
            self.agent_list.append(a)
            self.add_agent(a)
            aid += 1
        # Moderates: x ~ Uniform[-1, 1], u = U.
        for _ in range(self.n_moderate):
            x0 = self.rng.uniform(-1.0, 1.0)
            a = RAAgent(aid, self, opinion=x0, uncertainty=self.big_u, is_extremist=False)
            self.agent_list.append(a)
            self.add_agent(a)
            aid += 1

        self.reporter = DataCollector({
            "max_move": lambda m: m._sweep_max_move,
            "y": lambda m: m.polarization_y(),
        })

    # -- the elementary relative-agreement interaction --
    def interact(self, i: RAAgent, j: RAAgent) -> float:
        """One relative-agreement encounter: influencer ``i`` acts on influenced ``j``.

        Fires ONLY IF the segment overlap ``h_ij`` exceeds ``i``'s uncertainty
        ``u_i``. When it fires, with ``ra = h_ij / u_i - 1``:
            x_j += mu * ra * (x_i - x_j)
            u_j += mu * ra * (u_i - u_j)
        Only ``j`` is modified. Returns the magnitude of ``j``'s opinion change (0.0 if
        the interaction did not fire). Reads/writes only these two agents — no global
        state. The denominator is ``u_i`` (the influencer's uncertainty), not ``2*u_i``.
        """
        hi = min(i.x + i.u, j.x + j.u) - max(i.x - i.u, j.x - j.u)
        # Interaction fires only when the overlap strictly exceeds the influencer's u.
        if hi <= i.u:
            return 0.0
        ra = hi / i.u - 1.0
        dx = self.mu * ra * (i.x - j.x)
        du = self.mu * ra * (i.u - j.u)
        j.x += dx
        j.u += du
        return abs(dx)

    def random_ordered_pair(self) -> tuple:
        """Draw an ORDERED pair of DISTINCT agents (influencer i, influenced j)
        uniformly at random from the roster."""
        i = self.rng.randrange(self.n)
        j = self.rng.randrange(self.n)
        while j == i:
            j = self.rng.randrange(self.n)
        return self.agent_list[i], self.agent_list[j]

    # -- metrics --
    def opinions(self) -> List[float]:
        return [a.x for a in self.agent_list]

    def moderate_opinions(self) -> List[float]:
        """Final opinions of the INITIALLY-MODERATE agents (the graded population)."""
        return [a.x for a in self.agent_list if not a.is_extremist]

    def capture_fractions(self) -> tuple:
        """(p'_+, p'_-) = fractions of initially-moderate agents ending near the + and -
        extremes (``|x| > x_extreme_tol`` on the correct side). Zero moderates → (0, 0)."""
        mods = self.moderate_opinions()
        if not mods:
            return 0.0, 0.0
        n_pos = sum(1 for x in mods if x > self.x_extreme_tol)
        n_neg = sum(1 for x in mods if x < -self.x_extreme_tol)
        return n_pos / len(mods), n_neg / len(mods)

    def polarization_y(self) -> float:
        """The locked metric ``y = p'_+^2 + p'_-^2`` over initially-moderate agents.

        y ~ 0 : moderates stay central (neither pole captures them).
        y ~ 0.5: moderates split ~evenly between the two poles (double extreme).
        y ~ 1 : a single pole captures ~all moderates (single extreme)."""
        p_pos, p_neg = self.capture_fractions()
        return p_pos * p_pos + p_neg * p_neg

    def moderate_captured_fraction(self) -> float:
        """Fraction of initially-moderate agents ending at EITHER extreme
        (``|x| > x_extreme_tol``) — the 'moderate-capture' quantity used by P1/P2."""
        p_pos, p_neg = self.capture_fractions()
        return p_pos + p_neg

    def central_mean_abs_x(self) -> float:
        """Mean ``|x|`` over the initially-moderate agents that are NOT captured
        (``|x| <= x_extreme_tol``) — how central the surviving central cluster is.
        No such agents → 0.0."""
        central = [x for x in self.moderate_opinions() if abs(x) <= self.x_extreme_tol]
        if not central:
            return 0.0
        return sum(abs(x) for x in central) / len(central)

    def moderate_mean_x(self) -> float:
        """Mean signed opinion over all initially-moderate agents (population balance)."""
        mods = self.moderate_opinions()
        if not mods:
            return 0.0
        return sum(mods) / len(mods)

    # -- tick (one sweep = N random ordered-pair interactions) --
    def step(self) -> None:
        """One sweep: N random ordered-pair interactions. Track the largest single
        opinion change across the sweep, advance ``t``, and record per-sweep metrics."""
        max_move = 0.0
        for _ in range(self.n):
            i, j = self.random_ordered_pair()
            move = self.interact(i, j)
            if move > max_move:
                max_move = move
        self._sweep_max_move = max_move
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_sweeps: int = 400) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_sweeps`` sweeps (each = N random ordered-pair interactions) and
        return the run summary. The 2002 study runs to a frozen attractor; a fixed
        sweep budget well past freezing is used (checked adequate in FINDINGS)."""
        if n_sweeps <= 0:
            raise ValueError(f"need n_sweeps > 0 (got {n_sweeps})")
        self.reporter.collect(self)              # t=0 baseline
        for _ in range(n_sweeps):
            self.step()
        p_pos, p_neg = self.capture_fractions()
        return {
            "n": self.n,
            "mu": self.mu,
            "p_e": self.p_e,
            "u_e": self.u_e,
            "U": self.big_u,
            "delta": self.delta,
            "x_extreme_tol": self.x_extreme_tol,
            "seed": self.seed_value,
            "n_sweeps": n_sweeps,
            "n_extreme": self.n_extreme,
            "n_pos_extreme": self.n_pos_extreme,
            "n_neg_extreme": self.n_neg_extreme,
            "n_moderate": self.n_moderate,
            "y": self.polarization_y(),
            "p_plus": p_pos,
            "p_minus": p_neg,
            "moderate_captured_fraction": self.moderate_captured_fraction(),
            "central_mean_abs_x": self.central_mean_abs_x(),
            "moderate_mean_x": self.moderate_mean_x(),
            "final_moderate_opinions": self.moderate_opinions(),
            "final_opinions": self.opinions(),
            "max_move_series": self.reporter.series("max_move"),
            "y_series": self.reporter.series("y"),
        }


# -- run helpers --------------------------------------------------------------

def run_single(n: int = 200, *, mu: float = 0.5, p_e: float = 0.2, u_e: float = 0.1,
               big_u: float = 0.4, delta: float = 0.0, x_extreme_tol: float = 0.8,
               seed: int = 0, n_sweeps: int = 400) -> Dict[str, Any]:
    """One relative-agreement run at a given seed and (U, delta) condition."""
    return RelativeAgreementModel(n, mu=mu, p_e=p_e, u_e=u_e, big_u=big_u, delta=delta,
                                  x_extreme_tol=x_extreme_tol, seed=seed).run(n_sweeps)


def run_many_seeds(n: int = 200, *, mu: float = 0.5, p_e: float = 0.2, u_e: float = 0.1,
                   big_u: float = 0.4, delta: float = 0.0, x_extreme_tol: float = 0.8,
                   n_seeds: int = 20, seed_base: int = 0,
                   n_sweeps: int = 400) -> Dict[str, Any]:
    """Run ``n_seeds`` relative-agreement runs (seed ``seed_base + i``) at a fixed
    (U, delta) condition and summarise the polarization metric y, the moderate-capture
    fraction, the central-cluster |x|, and the pole balance across seeds.

    Returns per-seed y / capture / p_+ / p_- / central-|x| / mean-x, their means and
    ranges, the per-seed single-pole outcome (for P3's single-extreme test), and one
    representative y-trajectory (first seed).
    """
    if n_seeds <= 0:
        raise ValueError(f"need n_seeds > 0 (got {n_seeds})")
    runs = [run_single(n, mu=mu, p_e=p_e, u_e=u_e, big_u=big_u, delta=delta,
                       x_extreme_tol=x_extreme_tol, seed=seed_base + i, n_sweeps=n_sweeps)
            for i in range(n_seeds)]
    per_seed_y = [r["y"] for r in runs]
    per_seed_capture = [r["moderate_captured_fraction"] for r in runs]
    per_seed_p_plus = [r["p_plus"] for r in runs]
    per_seed_p_minus = [r["p_minus"] for r in runs]
    per_seed_central = [r["central_mean_abs_x"] for r in runs]
    per_seed_mean_x = [r["moderate_mean_x"] for r in runs]

    def _mean(xs: Sequence[float]) -> float:
        return sum(xs) / len(xs)

    return {
        "n": n, "mu": mu, "p_e": p_e, "u_e": u_e, "U": big_u, "delta": delta,
        "x_extreme_tol": x_extreme_tol,
        "n_seeds": n_seeds, "seed_base": seed_base, "n_sweeps": n_sweeps,
        "n_extreme": runs[0]["n_extreme"],
        "n_pos_extreme": runs[0]["n_pos_extreme"],
        "n_neg_extreme": runs[0]["n_neg_extreme"],
        "n_moderate": runs[0]["n_moderate"],
        "per_seed_y": per_seed_y,
        "per_seed_capture": per_seed_capture,
        "per_seed_p_plus": per_seed_p_plus,
        "per_seed_p_minus": per_seed_p_minus,
        "per_seed_central_abs_x": per_seed_central,
        "per_seed_moderate_mean_x": per_seed_mean_x,
        "mean_y": _mean(per_seed_y),
        "min_y": min(per_seed_y),
        "max_y": max(per_seed_y),
        "mean_capture": _mean(per_seed_capture),
        "min_capture": min(per_seed_capture),
        "max_capture": max(per_seed_capture),
        "mean_central_abs_x": _mean(per_seed_central),
        "mean_abs_moderate_mean_x": _mean([abs(m) for m in per_seed_mean_x]),
        "example_y_series": runs[0]["y_series"],
        "runs": runs,
    }


def single_pole_capture_stats(runs: Sequence[Dict[str, Any]], *,
                              dominant_bar: float = 0.9,
                              opposite_bar: float = 0.1) -> Dict[str, Any]:
    """Summarise the SINGLE-EXTREME outcome across a seed sweep (for P3).

    A seed is a 'single-pole capture' iff ONE pole captures > ``dominant_bar`` of the
    initially-moderate agents while the OPPOSITE captures < ``opposite_bar``. For each
    such seed, record which pole won (+ or -). Returns the count/fraction of single-pole
    seeds and, among them, the fraction whose winning pole is the + pole (the + majority
    of extremists), so the caller can grade 'the captured pole matches the + majority'.
    """
    single = []
    for r in runs:
        p_pos = r["p_plus"]
        p_neg = r["p_minus"]
        if p_pos > dominant_bar and p_neg < opposite_bar:
            single.append(("+", r))
        elif p_neg > dominant_bar and p_pos < opposite_bar:
            single.append(("-", r))
    n_single = len(single)
    n_total = len(runs)
    n_plus_won = sum(1 for pole, _ in single if pole == "+")
    return {
        "n_total": n_total,
        "n_single_pole": n_single,
        "frac_single_pole": (n_single / n_total) if n_total else 0.0,
        "n_plus_won": n_plus_won,
        "n_minus_won": n_single - n_plus_won,
        "frac_plus_among_single": (n_plus_won / n_single) if n_single else 0.0,
        "single_pole_poles": [pole for pole, _ in single],
    }
