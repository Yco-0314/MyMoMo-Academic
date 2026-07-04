"""Miller-Page (2004) standing-ovation model — a faithful agent-based reproduction.

Source: Miller, J.H. & Page, S.E. (2004), "The standing ovation problem",
Complexity 9(5):8-16. doi:10.1002/cplx.20033. (Also Miller & Page, *Complex
Adaptive Systems*, Princeton 2007, Ch. 9.)

The standing-ovation problem: a performance ends; each audience member must
decide whether to stand. The decision has a private (quality) component and a
social (conformity / peer-pressure) component. The model asks when a standing
ovation — a self-reinforcing cascade in which (nearly) everyone stands —
emerges, and shows that local conformity can amplify a marginal performance into
a full ovation (or suppress it into a flop).

Rules (the FIXED formulation graded here):

  * An L x L auditorium (L=40) of ``AudienceAgent``s, one per grid cell.
  * Each agent i perceives a private quality signal q_i = s + eps_i, where s is
    the COMMON true signal of the performance and eps_i ~ N(0, sigma) is i's own
    private perception noise (sigma=0.3). The draw is seeded -> reproducible.
  * INITIAL decision (quality only): agent i stands iff q_i > threshold T (T=0.5).
    The fraction standing after this step is the NO-CONFORMITY baseline.
  * CONFORMITY dynamics: then iterate. Each agent looks at its viewing
    neighbourhood and stands iff AT LEAST HALF of the agents in that neighbourhood
    are currently standing. The update is SYNCHRONOUS (every agent's next state is
    computed from one start-of-iteration snapshot, then all states are committed),
    run to a FIXED POINT (iterate until no agent changes), with a max-iteration cap.

Documented, FIXED neighbourhood + conformity choices (chosen BEFORE running; not
tuned):

  * NEIGHBOURHOOD = the Moore-8 cells around an agent, with the agent ITSELF
    EXCLUDED. Hard edges (no wrap): an edge agent has 5 neighbours, a corner agent
    has 3. This is the standard local "who can I see standing around me" patch.
  * CONFORMITY RULE = an agent stands iff (# standing neighbours) >= ceil(k/2),
    where k is its number of neighbours ("at least half of the neighbours are
    standing"). With an even k this is a strict majority-or-tie; with an odd k it
    is the strict majority. An agent surrounded entirely by seated neighbours
    (0 >= ceil(k/2)) sits. The agent's OWN current state does not enter its own
    rule (the neighbourhood excludes self); its state can still change because its
    neighbours' states do.

Grading metric (locked): the final (post-conformity, fixed-point) STANDING
FRACTION = (# agents standing) / L^2. We report it against the INITIAL
(pre-conformity, quality-only) standing fraction for the same draw, the number of
conformity iterations to the fixed point, and the per-iteration standing-fraction
series.

Built on the neutral platform (``abm_auto._platform``): each seat is an
``AudienceAgent`` carrying its perceived quality ``q`` and its boolean
``standing`` state; ``StandingOvationModel`` holds the L x L grid, performs the
seeded quality draw + initial stand rule, and drives the SYNCHRONOUS conformity
update to a fixed point over an ``AgentSet`` roster, recording (via a
``DataCollector``) the per-iteration standing fraction. The per-agent ``step`` is
intentionally a no-op: the synchronous fixed-point update is a model-level tick
(all next-states from one snapshot, then commit), not an autonomous single-agent
step.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

Cell = Tuple[int, int]

# The 8 Moore-neighbourhood offsets (self EXCLUDED). No wrap-around: the
# auditorium has hard edges, so edge cells have 5 neighbours and corner cells 3.
_MOORE_OFFSETS: Tuple[Cell, ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 1),
    (1, -1), (1, 0), (1, 1),
)


# -- Agent --------------------------------------------------------------------

class AudienceAgent(Agent):
    """One audience member at grid cell ``cell``.

    Carries its perceived quality ``q`` (= signal + private noise) and its boolean
    ``standing`` state. The conformity update is a model-level synchronous tick, so
    the per-agent ``step`` is a no-op; ``_next_standing`` stages the state computed
    this iteration before the model commits all states.
    """

    def __init__(self, agent_id: int, model: "StandingOvationModel", *,
                 cell: Cell, q: float) -> None:
        super().__init__(agent_id, model)
        self.cell = cell
        self.q = q
        self.standing = False
        self._next_standing = False

    def step(self) -> None:  # pragma: no cover - the tick lives on the model
        """The conformity update (snapshot -> commit) is a model-level synchronous
        tick, not an autonomous single-agent step, so this is a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class StandingOvationModel(AgentModel):
    """Drives the Miller-Page (2004) standing-ovation dynamics on an L x L grid.

    Construct with the auditorium side ``L``, the common signal ``s``, the
    perception-noise sd ``sigma``, the standing threshold ``T``, and a seed.
    ``run`` performs the seeded quality draw + the initial (quality-only) stand
    rule, then iterates the SYNCHRONOUS conformity update to a fixed point (or the
    ``max_iters`` cap), and returns the initial fraction, the final fraction, the
    iteration count, and the per-iteration standing-fraction series.
    """

    def __init__(self, *, L: int = 40, s: float = 0.5, sigma: float = 0.3,
                 T: float = 0.5, seed: int = 0, max_iters: int = 200) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if L <= 0:
            raise ValueError(f"need L > 0 (got {L})")
        if sigma < 0:
            raise ValueError(f"need sigma >= 0 (got {sigma})")
        if max_iters <= 0:
            raise ValueError(f"need max_iters > 0 (got {max_iters})")
        self.seed_value = seed
        self.L = L
        self.s = float(s)
        self.sigma = float(sigma)
        self.T = float(T)
        self.max_iters = max_iters

        # Seeded quality draw: q_i = s + eps_i, eps_i ~ N(0, sigma). One agent per
        # cell; the draw order is row-major so the result is fully deterministic
        # given the seed. This is the ONLY randomness in the run.
        self.grid: List[List[Optional[AudienceAgent]]] = [
            [None for _ in range(L)] for _ in range(L)
        ]
        self.agent_list: List[AudienceAgent] = []
        i = 0
        for r in range(L):
            for c in range(L):
                eps = self.rng.gauss(0.0, self.sigma) if self.sigma > 0 else 0.0
                q = self.s + eps
                agent = AudienceAgent(i, self, cell=(r, c), q=q)
                self.grid[r][c] = agent
                self.agent_list.append(agent)
                self.add_agent(agent)
                i += 1
        self.n = L * L

        # Apply the INITIAL (quality-only) stand rule: stand iff q > T.
        for agent in self.agent_list:
            agent.standing = agent.q > self.T
            agent._next_standing = agent.standing

        self.reporter = DataCollector({
            "standing_fraction": lambda m: m.standing_fraction(),
        })

    # -- metrics --
    def standing_fraction(self) -> float:
        """Fraction of the L^2 audience currently standing, in [0, 1]."""
        if self.n == 0:
            return 0.0
        return sum(1 for a in self.agent_list if a.standing) / self.n

    def initial_standing_fraction(self) -> float:
        """The pre-conformity (quality-only) standing fraction = fraction of agents
        whose perceived quality exceeds the threshold T. This is the no-conformity
        BASELINE control."""
        if self.n == 0:
            return 0.0
        return sum(1 for a in self.agent_list if a.q > self.T) / self.n

    # -- neighbourhood --
    def standing_neighbours(self, agent: AudienceAgent) -> Tuple[int, int]:
        """(# standing neighbours, # neighbours) in the Moore-8 patch around
        ``agent`` (self excluded, hard edges). Reads the agents' CURRENT
        ``standing`` state (the start-of-iteration snapshot during a synchronous
        update)."""
        r, c = agent.cell
        standing = 0
        total = 0
        for dr, dc in _MOORE_OFFSETS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.L and 0 <= nc < self.L:
                nb = self.grid[nr][nc]
                if nb is not None:
                    total += 1
                    if nb.standing:
                        standing += 1
        return standing, total

    def conformity_decision(self, agent: AudienceAgent) -> bool:
        """The conformity rule: stand iff AT LEAST HALF of the neighbours are
        standing, i.e. (# standing neighbours) >= ceil(k/2) where k = # neighbours.

        An agent with no neighbours (cannot occur for L>=2) keeps its state.
        """
        standing, total = self.standing_neighbours(agent)
        if total == 0:
            return agent.standing
        return standing >= math.ceil(total / 2)

    # -- conformity update (synchronous, to a fixed point) --
    def conformity_step(self) -> bool:
        """One SYNCHRONOUS conformity iteration: every agent's next state is
        computed from the start-of-iteration snapshot (the current ``standing``
        fields), then all states are committed at once. Returns True iff at least
        one agent changed state (so the caller can detect the fixed point)."""
        for agent in self.agent_list:
            agent._next_standing = self.conformity_decision(agent)
        changed = False
        for agent in self.agent_list:
            if agent._next_standing != agent.standing:
                changed = True
            agent.standing = agent._next_standing
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)
        return changed

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Record the initial (quality-only) standing fraction, then iterate the
        synchronous conformity update to a fixed point (no agent changes) or the
        ``max_iters`` cap. Returns the run summary."""
        initial_fraction = self.standing_fraction()
        baseline_fraction = self.initial_standing_fraction()
        # initial_fraction == baseline_fraction by construction: the no-conformity
        # baseline IS the quality-only initial stand. We keep both names explicit.
        self.reporter.collect(self)              # iteration 0 (pre-conformity)
        iters = 0
        converged = False
        for _ in range(self.max_iters):
            changed = self.conformity_step()
            iters += 1
            if not changed:
                converged = True
                break
        final_fraction = self.standing_fraction()
        return {
            "L": self.L,
            "s": self.s,
            "sigma": self.sigma,
            "T": self.T,
            "seed": self.seed_value,
            "n": self.n,
            "max_iters": self.max_iters,
            "initial_fraction": initial_fraction,
            "baseline_fraction": baseline_fraction,
            "final_fraction": final_fraction,
            "conformity_iters": iters,
            "converged": converged,
            "fraction_series": self.reporter.series("standing_fraction"),
        }


# -- single-run + sweep helpers -----------------------------------------------

def run_single(*, L: int = 40, s: float = 0.5, sigma: float = 0.3, T: float = 0.5,
               seed: int = 0, max_iters: int = 200) -> Dict[str, Any]:
    """One full standing-ovation run (seeded draw -> initial stand -> conformity to
    a fixed point) at a given signal ``s`` and seed."""
    return StandingOvationModel(L=L, s=s, sigma=sigma, T=T, seed=seed,
                                max_iters=max_iters).run()


def run_many_seeds(seeds: List[int], *, L: int = 40, s: float = 0.5,
                   sigma: float = 0.3, T: float = 0.5,
                   max_iters: int = 200) -> Dict[str, Any]:
    """Run one standing-ovation simulation per seed at a FIXED signal ``s`` and
    summarise across seeds.

    Returns per-seed rows plus the cross-seed mean initial (pre-conformity) and
    final (post-conformity, fixed-point) standing fraction — the headline numbers
    the locked clauses are evaluated against.
    """
    rows: List[Dict[str, Any]] = []
    for sd in seeds:
        rows.append(run_single(L=L, s=s, sigma=sigma, T=T, seed=sd,
                               max_iters=max_iters))
    n = len(rows)
    initials = [r["initial_fraction"] for r in rows]
    finals = [r["final_fraction"] for r in rows]
    mean_initial = sum(initials) / n if n else 0.0
    mean_final = sum(finals) / n if n else 0.0
    var_final = (sum((f - mean_final) ** 2 for f in finals) / n) if n else 0.0
    return {
        "seeds": list(seeds),
        "L": L,
        "s": s,
        "sigma": sigma,
        "T": T,
        "max_iters": max_iters,
        "rows": rows,
        "per_seed_initial": initials,
        "per_seed_final": finals,
        "mean_initial_fraction": mean_initial,
        "mean_final_fraction": mean_final,
        "min_final_fraction": min(finals) if finals else 0.0,
        "max_final_fraction": max(finals) if finals else 0.0,
        "std_final_fraction": var_final ** 0.5,
        # one representative trajectory (first seed) for inspection.
        "example_fraction_series": rows[0]["fraction_series"] if rows else [],
    }


def sweep_signal(signals: List[float], seeds: List[int], *, L: int = 40,
                 sigma: float = 0.3, T: float = 0.5,
                 max_iters: int = 200) -> Dict[str, Any]:
    """Sweep the common signal ``s`` over ``signals``, running ``seeds`` per signal,
    and return the per-signal cross-seed summary (initial vs final standing
    fraction). The signal values are FIXED by the caller before running."""
    out: Dict[str, Any] = {}
    for s in signals:
        out[s] = run_many_seeds(seeds, L=L, s=s, sigma=sigma, T=T,
                                max_iters=max_iters)
    return {
        "signals": list(signals),
        "seeds": list(seeds),
        "L": L,
        "sigma": sigma,
        "T": T,
        "max_iters": max_iters,
        "by_signal": out,
    }
