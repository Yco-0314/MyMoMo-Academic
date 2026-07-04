"""Majority-vote model (de Oliveira 1992) — a faithful agent-based reproduction.

Source: de Oliveira, M.J. (1992) "Isotropic majority-vote model on a square
lattice", J. Stat. Phys. 66(1/2):273-281. doi:10.1007/BF01060069.

The majority-vote model is a non-equilibrium 2-state spin dynamics with up-down
(Z2) symmetry and a single control parameter, the noise q. It has no Hamiltonian
(no detailed balance), yet it sits in the Ising universality class: a continuous
order-disorder phase transition at a critical noise q_c. On the square lattice
with the 4 nearest neighbours (von Neumann neighbourhood) de Oliveira reports
q_c ~= 0.075.

Rules (verified against the paper):
  * L x L periodic (toroidal) lattice; every site i carries a spin s_i in {+1, -1}.
  * One UPDATE of site i:
      - compute the SIGN of the local field S_i = sign(sum of its 4 NN spins);
      - with probability (1 - q) the spin ALIGNS with the neighbourhood majority
        (s_i <- S_i), and with probability q it takes the MINORITY sign
        (s_i <- -S_i). Equivalently s_i <- -sign(S_i) with prob q.
      - TIE rule (von Neumann 4-NN can tie 2-2 -> neighbour sum 0): use the
        canonical S(0)=0 convention, so the spin flips with probability 1/2
        independent of q. This preserves up-down symmetry without inventing a
        majority sign where the local field is zero.
  * One SWEEP = N = L*L single-site updates in RANDOM-SEQUENTIAL order (each sweep
    is a fresh seeded permutation of all sites; updates within a sweep see each
    other's results — genuine asynchronous dynamics, the standard MC scheme).
  * Order parameter: the magnetization per spin m = (1/N) * sum_i s_i. The locked
    metric is |m| = |sum s| / N, measured AFTER an equilibration transient and
    time-averaged over a measurement window.

Built on the neutral platform (``abm_auto._platform``): each site is a
``VoterAgent`` carrying its own spin; ``MajorityVoteModel`` owns the seeded RNG,
the periodic-lattice neighbour map, the random-sequential sweep, and a
``DataCollector`` for the |m| series — NOT a hand-rolled god-loop. Deterministic
given a seed (one RNG chain drives the initial spins, every sweep permutation,
the (1-q)/q noise draws, and every tie flip coin).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class VoterAgent(Agent):
    """One lattice site holding a ``spin`` in {+1, -1}.

    The agent is a passive spin-holder: the majority-vote rule (owned by the
    model) reads the site's 4 nearest-neighbour spins and writes the new spin
    onto it. There is no autonomous per-agent ``step`` schedule here — the model
    drives random-sequential single-site updates — so ``step`` is a no-op kept
    only to satisfy the platform contract.
    """

    def __init__(self, agent_id: int, model: "MajorityVoteModel", *, spin: int) -> None:
        super().__init__(agent_id, model)
        self.spin = spin

    def step(self) -> None:  # majority-vote drives per-site updates, not a sweep
        pass


# -- Model --------------------------------------------------------------------

class MajorityVoteModel(AgentModel):
    """Drives the de Oliveira majority-vote dynamics on an L x L periodic lattice.

    Construct with the side length ``L``, the noise ``q``, and a seed. ``run``
    performs ``equilibration`` sweeps to relax the transient, then ``measurement``
    sweeps over which the order parameter |m| is collected and time-averaged, and
    returns a summary dict (the locked |m| plus the per-window series).
    """

    def __init__(self, *, L: int = 50, q: float = 0.075, seed: int = 0,
                 equilibration: int = 200, measurement: int = 200,
                 init_up_fraction: float = 0.5) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if L < 2:
            raise ValueError(f"L must be >= 2; got {L}")
        if not (0.0 <= q <= 1.0):
            raise ValueError(f"q must be in [0, 1]; got {q}")
        self.L = L
        self.q = q
        self.N = L * L
        self.equilibration = equilibration
        self.measurement = measurement

        # Precompute the 4 von-Neumann neighbour ids of every site on the torus.
        # Site id = r*L + c, neighbours wrap with modular arithmetic.
        self.neighbors: List[Tuple[int, int, int, int]] = [(0, 0, 0, 0)] * self.N
        for r in range(L):
            for c in range(L):
                i = r * L + c
                up = ((r - 1) % L) * L + c
                down = ((r + 1) % L) * L + c
                left = r * L + ((c - 1) % L)
                right = r * L + ((c + 1) % L)
                self.neighbors[i] = (up, down, left, right)

        # Initial spins: each site +1 with prob ``init_up_fraction``, else -1.
        # Drawn from the model RNG so the whole run is reproducible from the seed.
        self.sites: List[VoterAgent] = []
        for i in range(self.N):
            spin = 1 if self.rng.random() < init_up_fraction else -1
            agent = VoterAgent(i, self, spin=spin)
            self.sites.append(agent)
            self.add_agent(agent)

        # The collector records the LOCKED order parameter |m| each sweep.
        self.reporter = DataCollector({"abs_m": lambda m: m.abs_magnetization()})

    # -- metrics --
    def magnetization(self) -> float:
        """Signed magnetization per spin m = (1/N) * sum_i s_i, in [-1, 1]."""
        return sum(a.spin for a in self.sites) / self.N

    def abs_magnetization(self) -> float:
        """The LOCKED order parameter |m| = |sum s| / N, in [0, 1]."""
        return abs(self.magnetization())

    # -- one single-site update --
    def update_site(self, i: int) -> None:
        """Apply the majority-vote rule to site ``i`` (reads its 4 NN spins).

        S = sign(sum of the 4 neighbour spins). If S == 0, the canonical
        majority-vote transition probability reduces to an unbiased flip of the
        current spin, independent of q. Otherwise, with prob (1 - q) the spin
        aligns with S (majority); with prob q it takes -S (minority / noise).
        Reads only the 4 neighbour spins.
        """
        up, down, left, right = self.neighbors[i]
        nn_sum = (self.sites[up].spin + self.sites[down].spin
                  + self.sites[left].spin + self.sites[right].spin)
        if nn_sum > 0:
            majority = 1
        elif nn_sum < 0:
            majority = -1
        else:  # 2-2 tie: S(0)=0 -> flip current spin with probability 1/2.
            if self.rng.random() < 0.5:
                self.sites[i].spin = -self.sites[i].spin
            return
        # With prob q flip to the minority sign; else adopt the majority sign.
        if self.rng.random() < self.q:
            self.sites[i].spin = -majority
        else:
            self.sites[i].spin = majority

    # -- one random-sequential sweep --
    def sweep(self) -> None:
        """One sweep = N single-site updates in a fresh seeded random order."""
        order = list(range(self.N))
        self.rng.shuffle(order)
        for i in order:
            self.update_site(i)

    # -- run --
    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Equilibrate, then measure: run ``equilibration`` sweeps (discarded), then
        ``measurement`` sweeps over which |m| is collected and time-averaged. Returns
        the run summary (the time-averaged |m|, its window series, and config)."""
        for _ in range(self.equilibration):
            self.sweep()
        series: List[float] = []
        for _ in range(self.measurement):
            self.sweep()
            val = self.abs_magnetization()
            series.append(val)
            self.reporter.records.append({"abs_m": val})
            self.t += 1
        abs_m_mean = sum(series) / len(series) if series else 0.0
        var = (sum((x - abs_m_mean) ** 2 for x in series) / len(series)) if series else 0.0
        return {
            "L": self.L,
            "q": self.q,
            "N": self.N,
            "equilibration": self.equilibration,
            "measurement": self.measurement,
            "abs_m_mean": abs_m_mean,
            "abs_m_var": var,
            "abs_m_min": min(series) if series else 0.0,
            "abs_m_max": max(series) if series else 0.0,
            "abs_m_series": series,
            "final_magnetization": self.magnetization(),
        }


# -- sweep helpers ------------------------------------------------------------

def run_single(*, L: int = 50, q: float = 0.075, seed: int = 0,
               equilibration: int = 200, measurement: int = 200) -> Dict[str, Any]:
    """One majority-vote run at noise ``q``; returns the time-averaged |m| summary."""
    res = MajorityVoteModel(L=L, q=q, seed=seed, equilibration=equilibration,
                            measurement=measurement).run()
    res["seed"] = seed
    res["L"] = L  # keep the summary self-describing
    return res


def run_many_seeds(*, L: int = 50, q: float = 0.075, n_seeds: int = 5,
                   seed_base: int = 0, equilibration: int = 200,
                   measurement: int = 200) -> Dict[str, Any]:
    """Run ``n_seeds`` independent realisations at noise ``q`` and seed-average |m|.

    Each run uses seed ``seed_base + i`` (deterministic ensemble; fresh initial
    spins + dynamics per seed). Returns the seed-mean of the (already
    time-averaged) |m|, its spread (min/max/std across seeds), and the per-seed
    values. The LOCKED metric is this seed-mean |m|.
    """
    per_seed: List[Dict[str, Any]] = []
    abs_ms: List[float] = []
    for i in range(n_seeds):
        seed = seed_base + i
        res = run_single(L=L, q=q, seed=seed, equilibration=equilibration,
                         measurement=measurement)
        abs_ms.append(res["abs_m_mean"])
        per_seed.append({
            "seed": seed,
            "abs_m_mean": res["abs_m_mean"],
            "abs_m_var": res["abs_m_var"],
            "abs_m_min": res["abs_m_min"],
            "abs_m_max": res["abs_m_max"],
        })
    mean = sum(abs_ms) / len(abs_ms)
    var = sum((x - mean) ** 2 for x in abs_ms) / len(abs_ms)
    return {
        "L": L,
        "q": q,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "equilibration": equilibration,
        "measurement": measurement,
        "abs_m_mean": mean,                 # the LOCKED, seed-averaged metric
        "abs_m_std": var ** 0.5,
        "abs_m_min": min(abs_ms),
        "abs_m_max": max(abs_ms),
        "abs_m_per_seed": abs_ms,
        "per_seed": per_seed,
    }


def half_crossing(q_grid: List[float], abs_m: List[float],
                  level: float = 0.5) -> Optional[float]:
    """Linearly-interpolated noise q at which the seed-mean |m| curve first crosses
    ``level`` (default 0.5) on the way down.

    Walks the (q, |m|) grid left-to-right; at the first adjacent pair that brackets
    ``level`` (|m| goes from >= level to < level) it linearly interpolates the
    crossing q. Returns None if the curve never crosses (e.g. stays above or below
    ``level`` across the whole grid). The grid is assumed sorted ascending in q.
    """
    for a in range(len(q_grid) - 1):
        m0, m1 = abs_m[a], abs_m[a + 1]
        if m0 >= level > m1:
            q0, q1 = q_grid[a], q_grid[a + 1]
            if m0 == m1:
                return q0
            frac = (m0 - level) / (m0 - m1)
            return q0 + frac * (q1 - q0)
    return None


def is_monotone_non_increasing(values: List[float], *, tol: float = 1e-9) -> bool:
    """True iff ``values`` is non-increasing within a small tolerance (allows tiny
    seed-noise wiggles up to ``tol``)."""
    return all(values[k + 1] <= values[k] + tol for k in range(len(values) - 1))
