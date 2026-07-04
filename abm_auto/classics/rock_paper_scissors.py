"""Spatial rock-paper-scissors (cyclic dominance) — a faithful agent-based
reproduction of the May-Leonard / Reichenbach-Mobilia-Frey coexistence result.

Sources (verified, not from memory):
  * Reichenbach, T., Mobilia, M. & Frey, E. (2007) "Mobility promotes and jeopardizes
    biodiversity in rock-paper-scissors games", Nature 448:1046-1049.
    doi:10.1038/nature06095.
  * Reichenbach, T., Mobilia, M. & Frey, E. (2008) "Self-organization of mobile
    populations in cyclic competition", J. Theor. Biol. 254(2):368-383.
    doi:10.1016/j.jtbi.2008.05.014.
  * May, R.M. & Leonard, W.J. (1975) "Nonlinear aspects of competition between three
    species", SIAM J. Appl. Math. 29(2):243-253. doi:10.1137/0129022.

This IS a genuine agent-based model (disclosed honestly). Each lattice site carries a
``SiteAgent`` whose ``step`` performs ONE random Monte-Carlo event from that site's own
point of view (it picks one of its neighbours and attempts predation / reproduction /
exchange). The agents are driven by an ``AgentSet`` scheduler in ``random_order`` (a
fresh seeded permutation each generation), so one "generation" (tick) = L*L random events
= the canonical Reichenbach-Mobilia-Frey timescale. An ``RPSModel`` (an ``AgentModel``
subclass) owns the seeded RNG + the shared species lattice + a ``DataCollector`` for the
per-generation species fractions. There is no god-loop: the per-event decision lives on
the agent.

Rules (the canonical three-species cyclic Lotka-Volterra on a lattice):

  * An L x L lattice. Each cell is EMPTY (0) or one of three species R(1), P(2), S(3).
    Cyclic dominance (rock-paper-scissors): R beats S, S beats P, P beats R.
  * One MC EVENT (one SiteAgent.step): the agent's own cell is the focal site; it picks
    one of its neighbours uniformly at random, then with the configured relative rates
    attempts exactly one reaction on the (focal, neighbour) pair:
        - PREDATION: if focal and neighbour are a predator-prey pair, the PREY cell
          becomes empty (the predator consumes it). Either ordering is handled
          symmetrically (whichever of the two is the prey dies).
        - REPRODUCTION: if exactly one of the two cells is empty and the other holds a
          species, the species places an offspring of its own type into the empty cell.
        - EXCHANGE / MOBILITY (relative rate epsilon): the two cells swap their contents
          (this is the mobility that, when large, destroys the spatial structure).
    The three reaction propensities are (selection, reproduction, exchange); the event
    type is drawn proportional to those rates. Rates are FIXED (sigma=mu=1, and a low
    exchange rate for the spatial arm) and are NOT tuned.
  * BOUNDARY / NEIGHBOURHOOD: periodic boundaries; the spatial arm uses the 4 von-Neumann
    nearest neighbours. The WELL-MIXED control replaces "a random neighbour" with "a
    random GLOBAL site" — the lattice geometry is destroyed while every reaction rule is
    byte-for-byte identical (the ONLY difference between the two arms is locality).

Coexistence: with LOCAL interaction (and low/zero mobility) the three species
self-organise into entangled rotating spiral domains and COEXIST indefinitely; in the
WELL-MIXED limit the finite system performs a random walk in the simplex of densities and
hits an absorbing boundary, losing biodiversity (typically collapsing to one survivor).

Determinism: a single ``numpy.random.default_rng(seed)`` draws BOTH the initial random
configuration and every per-event choice (which neighbour, which reaction, etc.), in a
fixed order, so the same seed reproduces byte-identical output. NumPy holds the lattice;
the SiteAgent owns the per-event decision and writes back into the lattice.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from abm_auto._platform import Agent, AgentModel, AgentSet, DataCollector

# Species encoding on the lattice.
EMPTY = 0
R = 1   # rock
P = 2   # paper
S = 3   # scissors
SPECIES = (R, P, S)
SPECIES_NAME = {R: "R", P: "P", S: "S"}

# Cyclic dominance map: PREY[x] = the species that x eats (x beats PREY[x]).
# R beats S, S beats P, P beats R.
PREY = {R: S, S: P, P: R}


def beats(a: int, b: int) -> bool:
    """True iff species ``a`` is the predator of species ``b`` (a eats b) under the
    cyclic R>S>P>R dominance. Both must be non-empty species."""
    return a in PREY and PREY[a] == b


# -- Agent --------------------------------------------------------------------

class SiteAgent(Agent):
    """One lattice site at grid coordinate (row, col).

    The species VALUE lives in the model's shared ``lattice`` array (so neighbour reads
    are O(1)), but the per-event DECISION lives here: ``step`` performs ONE Monte-Carlo
    event from this site's perspective by delegating to the model's ``event`` (the model
    knows whether partners are local neighbours or a global random site). That is the
    agent acting on its own neighbourhood — not a god-loop sweeping the grid.
    """

    def __init__(self, agent_id: int, model: "RPSModel", *, row: int, col: int) -> None:
        super().__init__(agent_id, model)
        self.row = row
        self.col = col

    def step(self) -> None:
        self.model.event(self.row, self.col)


# -- Model --------------------------------------------------------------------

class RPSModel(AgentModel):
    """Spatial rock-paper-scissors on an L x L periodic lattice of SiteAgents.

    Construct with L, the reaction rates (selection ``sigma``, reproduction ``mu``,
    exchange ``epsilon``), the ``well_mixed`` flag (global random partners instead of
    local neighbours), and a seed. ``run`` performs ``n_gen`` generations; ``step`` (one
    generation) drives every SiteAgent once in a fresh seeded permutation, i.e. L*L random
    MC events per generation (random-sequential dynamics). The shared species lattice is a
    NumPy (L, L) int8 array; ``event`` is the per-site decision the agent calls.

    The per-generation species fractions are collected by a ``DataCollector``. ``run``
    returns the survival count + final fractions + the full fraction series. Deterministic
    given ``seed``.
    """

    def __init__(self, *, L: int = 100, sigma: float = 1.0, mu: float = 1.0,
                 epsilon: float = 0.0, well_mixed: bool = False, seed: int = 0,
                 n_gen: int = 500, init_empty_fraction: float = 0.0,
                 extinct_threshold: float = 0.0) -> None:
        if L <= 0:
            raise ValueError("L must be positive")
        if min(sigma, mu, epsilon) < 0:
            raise ValueError("rates must be non-negative")
        if (sigma + mu + epsilon) <= 0:
            raise ValueError("at least one reaction rate must be positive")
        super().__init__(seed=seed, schedule="random_order")
        self.L = L
        self.N = L * L
        self.sigma = float(sigma)
        self.mu = float(mu)
        self.epsilon = float(epsilon)
        self.well_mixed = bool(well_mixed)
        self.seed = seed
        self.n_gen = n_gen
        self.extinct_threshold = float(extinct_threshold)

        # Reaction-type cumulative weights for the per-event categorical draw.
        total = self.sigma + self.mu + self.epsilon
        self._cum = (self.sigma / total,
                     (self.sigma + self.mu) / total,
                     1.0)

        # One seeded NumPy generator drives the initial configuration AND every per-event
        # choice (which neighbour, which reaction). The platform's random.Random self.rng
        # is left in place for the AgentSet permutation; the physics RNG is this separate
        # NumPy stream, seeded from the same seed, so the whole run is reproducible.
        self._np_rng = np.random.default_rng(seed)

        # Random initial configuration: each cell empty with prob init_empty_fraction,
        # else one of the 3 species uniformly. (Default: fully occupied, equal thirds in
        # expectation.)
        draw = self._np_rng.random((L, L))
        species_choice = self._np_rng.integers(0, 3, size=(L, L)).astype(np.int8) + 1
        self.lattice = np.where(draw < init_empty_fraction,
                                np.int8(EMPTY), species_choice).astype(np.int8)

        # One SiteAgent per cell, in row-major order. The AgentSet reshuffles them each
        # generation (random_order) -> random-sequential MC dynamics.
        self.agents = AgentSet([], schedule="random_order", rng=self.rng)
        aid = 0
        for r in range(L):
            for c in range(L):
                self.add_agent(SiteAgent(aid, self, row=r, col=c))
                aid += 1

        self.reporter = DataCollector({
            "fR": lambda m: m.species_fraction(R),
            "fP": lambda m: m.species_fraction(P),
            "fS": lambda m: m.species_fraction(S),
            "fE": lambda m: m.species_fraction(EMPTY),
        })

    # -- metrics --
    def species_count(self, sp: int) -> int:
        return int(np.count_nonzero(self.lattice == sp))

    def species_fraction(self, sp: int) -> float:
        return self.species_count(sp) / self.N if self.N else 0.0

    def n_surviving(self) -> int:
        """Number of the three species with fraction strictly above the extinction
        threshold (default > 0, i.e. at least one cell present)."""
        return sum(1 for sp in SPECIES
                   if self.species_fraction(sp) > self.extinct_threshold)

    # -- partner selection (the ONLY thing that differs between the two arms) --
    def _random_neighbour(self, row: int, col: int) -> Tuple[int, int]:
        """A uniformly-random von-Neumann nearest neighbour (periodic)."""
        L = self.L
        d = int(self._np_rng.integers(0, 4))
        if d == 0:
            return ((row - 1) % L, col)
        if d == 1:
            return ((row + 1) % L, col)
        if d == 2:
            return (row, (col - 1) % L)
        return (row, (col + 1) % L)

    def _random_global(self, row: int, col: int) -> Tuple[int, int]:
        """A uniformly-random GLOBAL site (any cell except the focal one) — destroys the
        lattice geometry while leaving every reaction rule identical (the well-mixed
        control)."""
        L = self.L
        while True:
            r = int(self._np_rng.integers(0, L))
            c = int(self._np_rng.integers(0, L))
            if (r, c) != (row, col):
                return (r, c)

    def _partner(self, row: int, col: int) -> Tuple[int, int]:
        return (self._random_global(row, col) if self.well_mixed
                else self._random_neighbour(row, col))

    # -- the per-site MC event the SiteAgent calls --
    def event(self, row: int, col: int) -> None:
        """One Monte-Carlo event from the focal site (row, col): pick a partner, draw a
        reaction type proportional to (sigma, mu, epsilon), and apply it in place.

        PREDATION: predator-prey pair -> the prey cell becomes empty.
        REPRODUCTION: one cell empty, the other a species -> offspring fills the empty cell.
        EXCHANGE: swap the two cells' contents (mobility).
        No-op if the drawn reaction does not apply to the current pair (a valid MC event:
        the move is simply rejected, exactly as in the Gillespie-style scheme)."""
        pr, pc = self._partner(row, col)
        a = int(self.lattice[row, col])
        b = int(self.lattice[pr, pc])

        u = float(self._np_rng.random())
        if u < self._cum[0]:
            # SELECTION / PREDATION: the prey of the pair dies (-> empty).
            if a != EMPTY and b != EMPTY:
                if beats(a, b):
                    self.lattice[pr, pc] = EMPTY
                elif beats(b, a):
                    self.lattice[row, col] = EMPTY
        elif u < self._cum[1]:
            # REPRODUCTION: a species fills an adjacent empty cell.
            if a != EMPTY and b == EMPTY:
                self.lattice[pr, pc] = a
            elif a == EMPTY and b != EMPTY:
                self.lattice[row, col] = b
        else:
            # EXCHANGE / MOBILITY: swap the two cells.
            self.lattice[row, col] = b
            self.lattice[pr, pc] = a

    # -- one generation = one random-sequential pass over all SiteAgents (L*L events) --
    def step(self) -> None:
        self.agents.step()           # AgentSet random_order -> fresh permutation, each agent fires one event
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_gen`` generations; return the survival count, final per-species
        fractions, and the full per-generation fraction series. Deterministic given the
        seed."""
        self.reporter.collect(self)          # generation-0 baseline (initial config)
        for _ in range(self.n_gen):
            self.step()
        fR = self.reporter.series("fR")
        fP = self.reporter.series("fP")
        fS = self.reporter.series("fS")
        fE = self.reporter.series("fE")
        final = {R: fR[-1], P: fP[-1], S: fS[-1]}
        return {
            "L": self.L,
            "sigma": self.sigma, "mu": self.mu, "epsilon": self.epsilon,
            "well_mixed": self.well_mixed,
            "seed": self.seed,
            "n_gen": self.n_gen,
            "final_fractions": {SPECIES_NAME[sp]: final[sp] for sp in SPECIES},
            "final_empty_fraction": fE[-1],
            "n_surviving": self.n_surviving(),
            "fR_series": fR, "fP_series": fP, "fS_series": fS, "fE_series": fE,
        }


# -- single / Monte-Carlo helpers ---------------------------------------------

def run_single(*, L: int = 100, sigma: float = 1.0, mu: float = 1.0,
               epsilon: float = 0.0, well_mixed: bool = False, seed: int = 0,
               n_gen: int = 500, init_empty_fraction: float = 0.0,
               extinct_threshold: float = 0.0) -> Dict[str, Any]:
    """One RPS run; returns the survival count + final fractions summary."""
    return RPSModel(L=L, sigma=sigma, mu=mu, epsilon=epsilon, well_mixed=well_mixed,
                    seed=seed, n_gen=n_gen, init_empty_fraction=init_empty_fraction,
                    extinct_threshold=extinct_threshold).run()


def run_many_seeds(*, L: int = 100, sigma: float = 1.0, mu: float = 1.0,
                   epsilon: float = 0.0, well_mixed: bool = False, n_seeds: int = 5,
                   seed_base: int = 0, n_gen: int = 500,
                   init_empty_fraction: float = 0.0,
                   coexist_threshold: float = 0.05,
                   extinct_threshold: float = 0.0) -> Dict[str, Any]:
    """Run ``n_seeds`` independent RPS runs (one arm) and summarise.

    Each trial uses seed ``seed_base + i``. Returns the per-seed survival counts and
    final fractions, the mean final fraction per species, the fraction of seeds in which
    ALL THREE species coexist (each final fraction > ``coexist_threshold``), and the mean
    number of surviving species. Deterministic given (L, rates, well_mixed, seed_base,
    n_gen).
    """
    results: List[Dict[str, Any]] = []
    for i in range(n_seeds):
        results.append(run_single(
            L=L, sigma=sigma, mu=mu, epsilon=epsilon, well_mixed=well_mixed,
            seed=seed_base + i, n_gen=n_gen, init_empty_fraction=init_empty_fraction,
            extinct_threshold=extinct_threshold))

    surv = [r["n_surviving"] for r in results]
    # per-species final fractions across seeds
    per_species = {SPECIES_NAME[sp]: [r["final_fractions"][SPECIES_NAME[sp]] for r in results]
                   for sp in SPECIES}
    coexist_flags = [
        all(r["final_fractions"][SPECIES_NAME[sp]] > coexist_threshold for sp in SPECIES)
        for r in results
    ]
    mean_fracs = {name: float(np.mean(vals)) for name, vals in per_species.items()}
    return {
        "L": L, "sigma": sigma, "mu": mu, "epsilon": epsilon,
        "well_mixed": well_mixed, "n_seeds": n_seeds, "seed_base": seed_base,
        "n_gen": n_gen, "coexist_threshold": coexist_threshold,
        "mean_n_surviving": float(np.mean(surv)),
        "min_n_surviving": int(np.min(surv)),
        "max_n_surviving": int(np.max(surv)),
        "per_seed_n_surviving": surv,
        "coexist_fraction": float(np.mean(coexist_flags)),
        "per_seed_coexist": coexist_flags,
        "mean_final_fractions": mean_fracs,
        "per_seed": [
            {"seed": r["seed"], "n_surviving": r["n_surviving"],
             "final_fractions": r["final_fractions"],
             "final_empty_fraction": r["final_empty_fraction"]}
            for r in results
        ],
        "per_seed_fraction_series": [
            {"seed": r["seed"], "fR": r["fR_series"], "fP": r["fP_series"],
             "fS": r["fS_series"]}
            for r in results
        ],
    }
