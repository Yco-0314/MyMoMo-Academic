"""Mirollo-Strogatz pulse-coupled integrate-and-fire oscillators (1990) — a faithful
reproduction.

Source: Mirollo, R.E. & Strogatz, S.H. (1990), "Synchronization of pulse-coupled
biological oscillators", SIAM Journal on Applied Mathematics 50(6):1645-1662.
doi:10.1137/0150098.

Framing: **genuine-agent (integrate-and-fire oscillators, disclosed).** Each of the N
agents is an integrate-and-fire oscillator carrying its own phase; the dynamics are the
event-driven fire/reset/pulse-kick/absorption rules of Mirollo & Strogatz, driven agent by
agent (the firing oscillator pulls every other agent up). This is NOT the continuous
sinusoidal mean-field of Kuramoto: coupling here is DISCRETE pulses with hard state resets
and ABSORPTION (firings that coalesce), and synchrony is reached for almost every initial
condition with NO finite coupling threshold, depending on the curve's CONCAVITY.

Physics (the canonical Mirollo-Strogatz model):
  * N oscillators. Each carries a phase phi in [0, 1] that rises at unit rate. Its
    "voltage" is a smooth, monotone, CONCAVE-down charging curve x = f(phi):
        f(phi) = (1/b) * ln(1 + (e^b - 1) * phi),   b > 0
    which satisfies f(0)=0, f(1)=1, f' > 0, f'' < 0 (concave). Its exact inverse is
        f_inv(x) = (e^{b x} - 1) / (e^b - 1).
    The LINEAR control curve f(phi) = phi (b -> 0 limit, f_inv(x) = x) has NO concavity.
  * Event-driven evolution. Advance EVERY phase by the same amount dt = 1 - max_i phi_i,
    so the leading oscillator(s) reach phi = 1. The oscillator(s) at phi = 1 FIRE together as
    the firing group, which:
      - resets to phi = 0;
      - delivers ONE collective pulse of size epsilon to every OTHER oscillator j, pulling
        its voltage up: x_j -> min(1, x_j + epsilon),  i.e. phi_j -> f_inv(min(1, f(phi_j)+eps));
      - ABSORPTION: any oscillator driven to x_j >= 1 by THAT single pulse FIRES too, in the
        same instant, and having been driven to threshold TOGETHER it stays phase-locked with
        the group forever after (they are now indistinguishable — same phase, same future
        kicks). Absorbed oscillators coalesce into the one FIRING GROUP. Crucially this is a
        single collective pulse, NOT a domino: a phase-locked group behaves as one oscillator
        and emits one epsilon pulse, so an oscillator this pulse does not reach is NOT dragged
        over the edge by the newly-absorbed members re-firing (they emit no separate pulse).
  * Full synchrony = all N oscillators collapse into ONE firing group (they fire together
    every cycle thereafter). We detect it as: a single firing event (possibly grown by
    absorption) in which ALL N oscillators fire at once, equivalently one group label left.

Determinism: the only randomness is the seeded initial phase draw (phi_i ~ U(0,1),
distinct); every event afterwards is deterministic. A per-oscillator integer GROUP LABEL
tracks coalescence: when oscillator j is absorbed into the firing group it is relabelled to
the firer's group, and thereafter the whole group shares one phase. Full sync <=> one
distinct group label remains (equivalently all N fire in a single cascade).

Built on the neutral platform (``abm_auto._platform``): each oscillator is a
``FireflyAgent`` carrying (phase, group); ``MirolloStrogatzModel`` drives the event-driven
fire/absorb dynamics over the ``AgentSet`` roster and detects the all-in-one-group sync.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

from abm_auto._platform import Agent, AgentModel


# =============================================================================
# charging curve f and its exact inverse (concave for b>0; linear control b->0)
# =============================================================================

def f_curve(phi: float, b: float) -> float:
    """Concave-down charging curve x = f(phi) = (1/b) ln(1 + (e^b - 1) phi) for b > 0,
    with f(0)=0, f(1)=1, f' > 0, f'' < 0. For b == 0 this is the LINEAR control f(phi)=phi
    (no concavity)."""
    if phi <= 0.0:
        return 0.0
    if phi >= 1.0:
        return 1.0
    if b == 0.0:
        return phi
    return math.log1p((math.expm1(b)) * phi) / b


def f_inverse(x: float, b: float) -> float:
    """Exact inverse of ``f_curve``: phi = f_inv(x) = (e^{b x} - 1)/(e^b - 1) for b > 0;
    the identity phi = x for the linear control b == 0. Clamped to [0, 1]."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    if b == 0.0:
        return x
    return math.expm1(b * x) / math.expm1(b)


def is_concave(b: float) -> bool:
    """The curve is strictly concave-down iff b > 0; b == 0 is the linear control."""
    return b > 0.0


# =============================================================================
# Agent
# =============================================================================

class FireflyAgent(Agent):
    """One integrate-and-fire oscillator: a phase ``phi`` in [0, 1] rising at unit rate and
    an integer ``group`` label tracking coalescence under absorption.

    The event-driven fire/absorb dynamics are model-level (the firing oscillator pulls every
    other agent up), so the per-agent ``step`` is intentionally a no-op."""

    def __init__(self, agent_id: int, model: "MirolloStrogatzModel", *, phi: float) -> None:
        super().__init__(agent_id, model)
        self.phi = phi
        self.group = agent_id           # every oscillator starts in its own singleton group

    def step(self) -> None:  # pragma: no cover - the tick lives on the model
        return None


# =============================================================================
# Model — event-driven pulse-coupled dynamics with absorption
# =============================================================================

class MirolloStrogatzModel(AgentModel):
    """Drives the Mirollo-Strogatz pulse-coupled integrate-and-fire dynamics.

    Construct with N, coupling ``eps``, curve parameter ``b`` (b>0 concave, b==0 linear
    control), and a seed (fixes the initial phase draw). ``run_to_sync(max_cycles)`` advances
    event-driven cycles until either full synchrony (all N in one firing group) is reached or
    the cycle cap is hit; it returns whether sync was reached and after how many cycles.
    """

    #: numeric tolerance for "at threshold" / phase equality after coalescence.
    EPS_PHASE = 1e-12

    def __init__(self, n: int = 100, *, eps: float = 0.1, b: float = 3.0,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if eps <= 0.0:
            raise ValueError(f"need eps > 0 (got {eps})")
        if b < 0.0:
            raise ValueError(f"need b >= 0 (got {b}; b>0 concave, b==0 linear control)")
        self.n = int(n)
        self.eps = float(eps)
        self.b = float(b)
        self.seed_value = int(seed)

        # The ONLY randomness: distinct initial phases phi_i ~ U(0, 1) (seeded).
        self.agent_list: List[FireflyAgent] = []
        phases = self._distinct_phases(self.n)
        for i in range(self.n):
            agent = FireflyAgent(i, self, phi=phases[i])
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.cycles = 0            # firing events processed (leader-triggered)
        self.synced = False
        self.sync_cycle: Optional[int] = None

    def _distinct_phases(self, n: int) -> List[float]:
        """Draw ``n`` distinct initial phases in (0, 1). Distinctness avoids a degenerate
        exact tie at t=0 (measure zero for a real draw); re-draws only on the rare collision."""
        seen: set[float] = set()
        out: List[float] = []
        while len(out) < n:
            p = self.rng.random()
            if 0.0 < p < 1.0 and p not in seen:
                seen.add(p)
                out.append(p)
        return out

    # -- curve wrappers bound to this model's b --
    def f(self, phi: float) -> float:
        return f_curve(phi, self.b)

    def f_inv(self, x: float) -> float:
        return f_inverse(x, self.b)

    # -- group / sync bookkeeping --
    def n_groups(self) -> int:
        """Number of distinct firing groups currently alive (1 == full synchrony)."""
        return len({a.group for a in self.agent_list})

    def is_synced(self) -> bool:
        return self.n_groups() == 1

    def phases(self) -> List[float]:
        return [a.phi for a in self.agent_list]

    # -- one firing event (leader fires; absorption cascades) --
    def _advance_to_next_firing(self) -> float:
        """Advance every phase uniformly by dt = 1 - max phi so the leading oscillator(s)
        reach phi = 1. Returns dt (>= 0)."""
        max_phi = max(a.phi for a in self.agent_list)
        dt = 1.0 - max_phi
        if dt > 0.0:
            for a in self.agent_list:
                a.phi += dt
        return dt

    def _fire_cascade(self) -> int:
        """Process ONE firing event with absorption.

        The oscillator(s) at phi >= 1 fire together as the firing group. That group delivers
        exactly ONE collective pulse of size eps to every OTHER oscillator, pulling its voltage
        up: x_j -> min(1, x_j + eps), i.e. phi_j -> f_inv(min(1, f(phi_j)+eps)). Any oscillator
        whose voltage is driven to/over threshold by THAT single pulse is ABSORBED — it fires
        in the same instant and coalesces into the firing group's single label, so it stays
        phase-locked with them forever after. Every firer (original + absorbed) is then reset
        to phi = 0 together. Returns the number of oscillators that fired in this event.

        This is a SINGLE collective pulse, not a domino: a phase-locked firing group is one
        oscillator behaviourally, so it emits one eps pulse — an oscillator that this pulse
        does NOT push over threshold is not carried over the edge by the absorbed members
        re-firing (they are already in the group and emit no separate pulse). Coalescence is
        exact: all fired oscillators share ONE group label and reset to phi = 0 together, so
        from now on they receive identical kicks and remain identical.
        """
        fired: List[FireflyAgent] = [a for a in self.agent_list if a.phi >= 1.0 - self.EPS_PHASE]
        if not fired:
            return 0
        fired_set = set(id(a) for a in fired)
        # ONE collective eps pulse from the firing group to every not-yet-fired oscillator.
        # Absorption: any oscillator pushed to/over threshold by THIS pulse joins the group
        # (fires this instant). Applied in a single pass — the newly-absorbed do NOT emit a
        # fresh pulse (they are already phase-locked into the one firing group).
        for a in self.agent_list:
            if id(a) in fired_set:
                continue
            # pulse-kick j UP by eps in VOLTAGE: x_j -> min(1, x_j + eps).
            x_new = min(1.0, self.f(a.phi) + self.eps)
            a.phi = self.f_inv(x_new)
            if a.phi >= 1.0 - self.EPS_PHASE:
                # ABSORPTION: j is driven to threshold by the pulse -> it fires now, coalesces.
                fired_set.add(id(a))
                fired.append(a)
        # coalesce ALL firers (original + absorbed) into one group under the smallest label
        # (computed over the FINAL fired set so the surviving label is canonical and
        # order-independent), and reset them to 0 together (phase-locked forever).
        group_label = min(a.group for a in fired)
        for a in fired:
            a.phi = 0.0
            a.group = group_label
        return len(fired)

    def _step_event(self) -> int:
        """Advance to the next firing and process its cascade; return the cascade size."""
        self._advance_to_next_firing()
        n_fired = self._fire_cascade()
        self.cycles += 1
        return n_fired

    def run_to_sync(self, max_cycles: int = 4000) -> Dict[str, Any]:
        """Run event-driven firing cycles until full synchrony (all N in one firing group)
        or the ``max_cycles`` cap.

        Full sync is detected two equivalent ways (both used): all N oscillators fire in a
        single cascade, OR only one distinct group label remains. Returns whether sync was
        reached, the cycle at which it happened, the group count, and diagnostics.
        """
        if max_cycles <= 0:
            raise ValueError(f"need max_cycles > 0 (got {max_cycles})")
        if self.is_synced():                      # N == 1 edge case: already one group
            self.synced = True
            self.sync_cycle = 0
        max_cascade = 0
        while not self.synced and self.cycles < max_cycles:
            n_fired = self._step_event()
            if n_fired > max_cascade:
                max_cascade = n_fired
            if n_fired == self.n or self.is_synced():
                self.synced = True
                self.sync_cycle = self.cycles
        return {
            "n": self.n, "eps": self.eps, "b": self.b, "seed": self.seed_value,
            "concave": is_concave(self.b),
            "synced": self.synced,
            "cycles_to_sync": self.sync_cycle if self.synced else None,
            "cycles_run": self.cycles,
            "n_groups_final": self.n_groups(),
            "max_cascade": max_cascade,
            "max_cycles": max_cycles,
        }


# =============================================================================
# experiment helpers
# =============================================================================

def run_single(n: int = 100, *, eps: float = 0.1, b: float = 3.0, seed: int = 0,
               max_cycles: int = 4000) -> Dict[str, Any]:
    """One Mirollo-Strogatz run at a given (eps, b, seed); returns its sync summary."""
    return MirolloStrogatzModel(n, eps=eps, b=b, seed=seed).run_to_sync(max_cycles=max_cycles)


def run_many_seeds(n: int = 100, *, eps: float = 0.1, b: float = 3.0, n_seeds: int = 20,
                   seed_base: int = 0, max_cycles: int = 4000) -> Dict[str, Any]:
    """Run ``n_seeds`` runs (seed ``seed_base + i``) at fixed (N, eps, b) and summarise the
    synchronization outcome across seeds.

    Returns the fraction of seeds that reached full sync, the per-seed cycles-to-sync (None
    for seeds that did not sync within the cap), and the MEDIAN cycles-to-sync over the
    seeds that DID sync (the P2 speed metric). A seed that never syncs contributes to the
    sync fraction (as a failure) but not to the median (undefined for it)."""
    if n_seeds <= 0:
        raise ValueError(f"need n_seeds > 0 (got {n_seeds})")
    runs = [run_single(n, eps=eps, b=b, seed=seed_base + i, max_cycles=max_cycles)
            for i in range(n_seeds)]
    synced_flags = [r["synced"] for r in runs]
    n_synced = sum(synced_flags)
    sync_fraction = n_synced / n_seeds
    cyc = [r["cycles_to_sync"] for r in runs]
    synced_cycles = sorted(c for c in cyc if c is not None)
    median_cycles = _median(synced_cycles) if synced_cycles else None
    return {
        "n": n, "eps": eps, "b": b, "concave": is_concave(b),
        "n_seeds": n_seeds, "seed_base": seed_base, "max_cycles": max_cycles,
        "n_synced": n_synced, "sync_fraction": sync_fraction,
        "per_seed_synced": synced_flags,
        "per_seed_cycles_to_sync": cyc,
        "synced_cycles_sorted": synced_cycles,
        "median_cycles_to_sync": median_cycles,
        "mean_cycles_to_sync": (sum(synced_cycles) / len(synced_cycles)
                                if synced_cycles else None),
        "max_cascade_over_seeds": max(r["max_cascade"] for r in runs),
        "min_groups_final": min(r["n_groups_final"] for r in runs),
        "max_groups_final": max(r["n_groups_final"] for r in runs),
    }


def _median(sorted_vals: Sequence[float]) -> float:
    """Median of an already-sorted non-empty sequence."""
    k = len(sorted_vals)
    mid = k // 2
    if k % 2 == 1:
        return float(sorted_vals[mid])
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
