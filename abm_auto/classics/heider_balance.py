"""Heider social balance / Antal-Krapivsky-Redner (2005) constrained triad dynamics
(CTD) — a faithful reproduction of structural balance on a complete signed graph.

Source: Antal, T., Krapivsky, P.L. & Redner, S. (2005), "Dynamics of social balance on
networks", Phys. Rev. E 72(3):036121. doi:10.1103/PhysRevE.72.036121. Structural balance
itself originates with Heider, F. (1946), "Attitudes and cognitive organization",
J. Psychology 21:107-112.

IMPORTANT (honesty, binds the FINDINGS): this is **signed-network dynamics
(model-orchestrated triad/edge updates), NOT autonomous agent-stepping**. There is no
roster of agents that each perceive, decide and act on their own schedule; the dynamical
object is the *signed edge matrix* of a complete graph, and the model orchestrates the
updates: it repeatedly picks an imbalanced triangle and flips one of its edges. The nodes
are not Agents that ``step``. We disclose this exactly as the ER/WS network-generation and
the BTW sandpile reproductions disclose that they are not agent-stepping ABMs. The
lock-first + honest-verdict + L3-bundle discipline still fully applies. The model is built
on the neutral platform (``abm_auto._platform.AgentModel``) for the seeded-RNG + run-loop
floor, but the per-tick work is a model-level edge update, not an ``AgentSet.step``.

Model (complete signed graph, N=30):
  * Every unordered pair (i, j) carries a sign s_ij in {+1, -1}. Random init: each edge
    is +1 or -1 independently with probability 1/2 (seed-dependent; this is the only
    randomness besides the triangle/tie-break draws).
  * A triangle (i, j, k) is BALANCED iff the product of its three edge signs is +1
    (0 or 2 negative edges: "the friend of my friend is my friend", "the enemy of my
    enemy is my friend"). It is IMBALANCED / FRUSTRATED iff the product is -1 (1 or 3
    negative edges). FRUSTRATION (energy) = the number of imbalanced triangles.

CTD update step (Antal-Krapivsky-Redner 2005, documented exactly):
  1. Pick a uniformly random IMBALANCED triangle (i, j, k). (If none exist the state is
     absorbing / fully balanced and the run stops.)
  2. Flipping any ONE of its three edges turns THAT triangle balanced. But each edge is
     shared with the other N-2 triangles through it, so each candidate flip changes the
     GLOBAL imbalanced-triangle count by some Delta. Compute Delta for flipping each of the
     three edges. Delta for flipping edge (a, b) depends ONLY on the N-2 triangles through
     (a, b): a triangle (a, b, c) flips balance state iff the flip changes its product, so
     Delta = (#triangles through (a,b) that were balanced and become imbalanced) -
     (#that were imbalanced and become balanced) — the natural incremental inner loop.
  3. Flip the edge whose Delta is MOST NEGATIVE (greatest reduction in global frustration),
     breaking ties uniformly at random.
  4. CONSTRAINT (the AKR rule): accept the flip ONLY if its Delta <= 0 (energy
     non-increasing). If all three candidate flips would INCREASE global frustration
     (every Delta > 0), the move is REJECTED and another imbalanced triangle is drawn.
     This constraint guarantees the energy is monotonically non-increasing and, on a
     complete graph, drives the system to a BALANCED absorbing state — either "paradise"
     (all edges +) or two mutually-hostile factions (every intra-faction edge +, every
     inter-faction edge -).

Run to absorption (no imbalanced triangle remains) or a generous step cap, over >=10
seeds. Deterministic given a seed.

Efficient triangle counting (N=30 -> C(30,3)=4060 triangles): the global energy is
computed once by scanning all triangles; thereafter each accepted flip updates the energy
by its incremental Delta, and each candidate Delta only scans the N-2 triangles through the
one edge (O(N) per candidate, O(N) per step), never the full O(N^3) recount. The
brute-force recount is kept as a reference and pinned equal to the incremental Delta in the
tests.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import AgentModel


# -- triangle-balance predicate + global energy -------------------------------

def triad_is_balanced(s_ij: int, s_jk: int, s_ik: int) -> bool:
    """A triangle is BALANCED iff the product of its three edge signs is +1.

    Balanced = 0 or 2 negative edges (product +1); imbalanced/frustrated = 1 or 3 negative
    edges (product -1). This is the structural-balance predicate (Heider 1946)."""
    return s_ij * s_jk * s_ik > 0


def count_imbalanced_triangles(signs: List[List[int]]) -> int:
    """Global frustration / energy = number of imbalanced triangles in a complete signed
    graph given as a symmetric sign matrix ``signs`` (signs[i][j] in {+1,-1}, i != j).

    Brute-force O(N^3) over all C(N,3) triples — used to seed the energy once and as the
    reference the incremental Delta is checked against in the tests."""
    n = len(signs)
    bad = 0
    for i, j, k in combinations(range(n), 3):
        if not triad_is_balanced(signs[i][j], signs[j][k], signs[i][k]):
            bad += 1
    return bad


# -- faction-partition recovery (the P2 structural check) ---------------------

def recover_factions(signs: List[List[int]]) -> Optional[List[int]]:
    """Try to 2-colour the nodes from the sign structure of a BALANCED complete graph.

    A complete signed graph is structurally balanced iff its nodes partition into at most
    two groups such that every WITHIN-group edge is + and every BETWEEN-group edge is -
    (the "two hostile factions" theorem; the all-+ "paradise" is the degenerate one-group
    case). We recover the partition by fixing node 0 in group 0, then for every other node
    j: same group as 0 iff s[0][j] == +1, opposite group iff s[0][j] == -1. We then VERIFY
    the recovered 2-colouring is globally consistent: every same-group pair must be +, every
    cross-group pair must be -. Returns the colour list (0/1 per node) if consistent, else
    ``None`` (no valid <=2-faction balance, i.e. the structure is NOT balanced)."""
    n = len(signs)
    if n == 0:
        return []
    colour = [0] * n          # node 0 anchors group 0
    for j in range(1, n):
        colour[j] = 0 if signs[0][j] > 0 else 1
    # Verify consistency over ALL pairs (this is what makes it a proof, not a guess).
    for i, j in combinations(range(n), 2):
        same = colour[i] == colour[j]
        if same and signs[i][j] < 0:
            return None       # same group but a hostile edge -> not balanced
        if (not same) and signs[i][j] > 0:
            return None       # different groups but a friendly edge -> not balanced
    return colour


def is_valid_two_faction_balance(signs: List[List[int]]) -> bool:
    """True iff the final signs form a valid <=2-faction balance (paradise OR exactly two
    factions with + intra / - inter), verified by recovering a consistent 2-colouring."""
    return recover_factions(signs) is not None


def faction_sizes(signs: List[List[int]]) -> Optional[Tuple[int, int]]:
    """(size of group 0, size of group 1) for a balanced graph, or None if not balanced.
    A paradise (all +) returns (N, 0)."""
    colour = recover_factions(signs)
    if colour is None:
        return None
    g1 = sum(colour)
    return (len(colour) - g1, g1)


# -- the CTD model ------------------------------------------------------------

class HeiderBalanceModel(AgentModel):
    """Antal-Krapivsky-Redner (2005) constrained triad dynamics on a complete signed graph.

    Construct with N and a seed. The signed edge matrix is initialised with each edge +1 or
    -1 independently with probability 1/2 (seed-dependent). ``run`` orchestrates CTD steps
    until the graph is balanced (energy 0, absorbing) or a step cap is hit, recording the
    energy (imbalanced-triangle count) after every accepted flip.

    Signed-network dynamics, NOT agent-stepping: the nodes are not platform ``Agent``s and
    there is no per-agent ``step``; the model owns the edge matrix and drives the updates.
    We ride ``AgentModel`` only for its seeded RNG + the deterministic run-loop floor.
    """

    def __init__(self, n: int = 30, *, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n < 3:
            raise ValueError(f"need n >= 3 for triangles (got {n})")
        self.seed_value = seed
        self.n = n
        # Symmetric sign matrix; diagonal unused (kept 0). Random ±1 init, prob 1/2 each.
        self.signs: List[List[int]] = [[0] * n for _ in range(n)]
        for i, j in combinations(range(n), 2):
            s = 1 if self.rng.random() < 0.5 else -1
            self.signs[i][j] = s
            self.signs[j][i] = s
        # Seed the global energy once (brute force); thereafter it is updated incrementally.
        self.energy = count_imbalanced_triangles(self.signs)
        # Energy series: index 0 is the initial energy, then one entry per ACCEPTED flip.
        self.energy_series: List[int] = [self.energy]
        self.n_steps = 0          # accepted flips
        self.n_rejected = 0       # drawn imbalanced triangles whose every flip raised energy

    # -- balance bookkeeping --
    def is_balanced(self) -> bool:
        """Absorbing iff no imbalanced triangle remains (energy 0)."""
        return self.energy == 0

    def imbalanced_triangles(self) -> List[Tuple[int, int, int]]:
        """All currently imbalanced triangles (i<j<k). Used to draw a random one; O(N^3)
        but only built when a step needs a fresh imbalanced triangle to act on."""
        out: List[Tuple[int, int, int]] = []
        s = self.signs
        for i, j, k in combinations(range(self.n), 3):
            if not triad_is_balanced(s[i][j], s[j][k], s[i][k]):
                out.append((i, j, k))
        return out

    # -- the incremental Delta for flipping one edge --
    def delta_for_flip(self, a: int, b: int) -> int:
        """Global change in the imbalanced-triangle count if edge (a, b) is flipped.

        Only the N-2 triangles through (a, b) can change balance state, so we scan just
        those: for each third node c, the triangle (a, b, c) is currently balanced or not;
        flipping s_ab flips its product, hence flips its balance state. Delta = (number that
        go balanced -> imbalanced) - (number that go imbalanced -> balanced). This is the
        exact incremental equivalent of recounting the whole graph after the flip (pinned in
        the tests)."""
        s = self.signs
        s_ab = s[a][b]
        flipped = -s_ab
        delta = 0
        for c in range(self.n):
            if c == a or c == b:
                continue
            s_ac = s[a][c]
            s_bc = s[b][c]
            was_balanced = (s_ab * s_ac * s_bc) > 0
            now_balanced = (flipped * s_ac * s_bc) > 0
            if was_balanced and not now_balanced:
                delta += 1
            elif (not was_balanced) and now_balanced:
                delta -= 1
        return delta

    def _apply_flip(self, a: int, b: int, delta: int) -> None:
        """Commit an accepted flip of edge (a, b): flip both symmetric entries and update
        the global energy by the precomputed incremental Delta."""
        self.signs[a][b] = -self.signs[a][b]
        self.signs[b][a] = self.signs[a][b]
        self.energy += delta

    # -- one CTD step (model-orchestrated; NOT an agent step) --
    def ctd_step(self) -> bool:
        """One constrained-triad-dynamics step.

        Draw a uniformly random imbalanced triangle; compute the three candidate edge-flip
        Deltas; among the most-negative Delta choose uniformly at random (tie-break); accept
        ONLY if that Delta <= 0 (energy non-increasing), else REJECT and report no progress.
        Returns True iff an accepted flip occurred (energy recorded), False if the drawn
        triangle's every flip would raise energy (rejected) or the graph is already balanced.

        The accept-only-if-Delta<=0 constraint is the AKR rule that makes the energy
        monotonically non-increasing. Because the chosen edge belongs to the drawn imbalanced
        triangle, flipping it always balances THAT triangle (a local -1 contribution), so the
        most-negative candidate Delta is <= 0 in the overwhelming majority of draws; the
        explicit Delta<=0 guard is what enforces strict non-increase even in the rare frustrated
        configurations where balancing one triangle would imbalance more than one elsewhere."""
        if self.is_balanced():
            return False
        bad = self.imbalanced_triangles()
        # Draw one uniformly at random.
        i, j, k = bad[self.rng.randrange(len(bad))]
        candidates = [(i, j), (j, k), (i, k)]
        deltas = [self.delta_for_flip(a, b) for (a, b) in candidates]
        best = min(deltas)
        if best > 0:
            # Every flip would increase global frustration -> reject (AKR constraint).
            self.n_rejected += 1
            return False
        # Among the most-negative Delta, break ties uniformly at random.
        best_idx = [idx for idx, d in enumerate(deltas) if d == best]
        chosen = best_idx[self.rng.randrange(len(best_idx))]
        a, b = candidates[chosen]
        self._apply_flip(a, b, best)
        self.n_steps += 1
        self.energy_series.append(self.energy)
        return True

    def run(self, max_steps: int = 200_000, *,                      # type: ignore[override]
            max_rejections: Optional[int] = None) -> Dict[str, Any]:
        """Orchestrate CTD steps until the graph is balanced (absorbing) or a cap is hit.

        Draws imbalanced triangles and applies accepted flips. A draw whose every flip would
        raise energy is rejected (another triangle is drawn); the run stops on absorption
        (energy 0), on ``max_steps`` accepted flips, or — to avoid spinning forever in a
        rare frustrated trap — after ``max_rejections`` consecutive rejections (default
        10*C(N,3), generous). Returns the run summary including the final sign matrix, the
        full energy series, whether balance was reached, and the recovered faction partition.
        """
        if max_rejections is None:
            # Generous: 10x the number of triangles. A genuine trap rejects every triangle
            # repeatedly; a still-progressing run resets the counter on any accepted flip.
            tri = self.n * (self.n - 1) * (self.n - 2) // 6
            max_rejections = 10 * tri
        consecutive_rejections = 0
        while not self.is_balanced() and self.n_steps < max_steps:
            progressed = self.ctd_step()
            if progressed:
                consecutive_rejections = 0
            else:
                consecutive_rejections += 1
                if consecutive_rejections >= max_rejections:
                    break       # stuck (rare frustrated trap); report honestly, do not loop
        colour = recover_factions(self.signs)
        sizes = faction_sizes(self.signs)
        return {
            "n": self.n,
            "seed": self.seed_value,
            "reached_balance": self.is_balanced(),
            "final_energy": self.energy,
            "initial_energy": self.energy_series[0],
            "n_steps": self.n_steps,
            "n_rejected": self.n_rejected,
            "energy_series": list(self.energy_series),
            "energy_non_increasing": _is_non_increasing(self.energy_series),
            "is_two_faction_balance": colour is not None,
            "faction_partition": colour,
            "faction_sizes": list(sizes) if sizes is not None else None,
            "is_paradise": (colour is not None and (sizes[0] == self.n or sizes[1] == self.n))
                           if sizes is not None else False,
            "final_signs": [row[:] for row in self.signs],
        }


# -- helpers ------------------------------------------------------------------

def _is_non_increasing(series: List[int]) -> bool:
    """True iff the series never increases (each term <= the previous)."""
    return all(series[t + 1] <= series[t] for t in range(len(series) - 1))


def run_single(n: int = 30, *, seed: int = 0,
               max_steps: int = 200_000) -> Dict[str, Any]:
    """One CTD run to absorption at a given seed. Deterministic given ``seed``."""
    return HeiderBalanceModel(n, seed=seed).run(max_steps=max_steps)


def run_many_seeds(n: int = 30, *, n_seeds: int = 10, seed_base: int = 0,
                   max_steps: int = 200_000) -> Dict[str, Any]:
    """Run ``n_seeds`` CTD runs (seed ``seed_base + i``) to absorption and summarise.

    Returns the per-run reached-balance flags, energy non-increase flags, valid-<=2-faction
    flags, paradise-vs-two-faction breakdown, faction sizes, step counts, the fraction of
    seeds that reached balance, and one representative energy series (first seed) for
    inspection / plotting.
    """
    runs = [run_single(n, seed=seed_base + i, max_steps=max_steps) for i in range(n_seeds)]
    reached = [r["reached_balance"] for r in runs]
    non_inc = [r["energy_non_increasing"] for r in runs]
    valid2 = [r["is_two_faction_balance"] for r in runs]
    paradise = [r["is_paradise"] for r in runs]
    two_faction = [bool(r["is_two_faction_balance"] and not r["is_paradise"]) for r in runs]
    return {
        "n": n,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "max_steps": max_steps,
        "per_seed_reached_balance": reached,
        "per_seed_energy_non_increasing": non_inc,
        "per_seed_valid_two_faction": valid2,
        "per_seed_is_paradise": paradise,
        "per_seed_is_two_faction": two_faction,
        "per_seed_initial_energy": [r["initial_energy"] for r in runs],
        "per_seed_final_energy": [r["final_energy"] for r in runs],
        "per_seed_n_steps": [r["n_steps"] for r in runs],
        "per_seed_faction_sizes": [r["faction_sizes"] for r in runs],
        "frac_reached_balance": sum(reached) / n_seeds,
        "frac_energy_non_increasing": sum(non_inc) / n_seeds,
        "frac_valid_two_faction": sum(valid2) / n_seeds,
        "n_paradise": sum(paradise),
        "n_two_faction": sum(two_faction),
        # one representative trajectory (first seed) for plotting/inspection.
        "example_energy_series": runs[0]["energy_series"],
    }
