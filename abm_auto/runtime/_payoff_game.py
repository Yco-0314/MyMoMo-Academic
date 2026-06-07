"""ABM Auto Runtime — PayoffGame, a library game-theory operator (ADR-014 Phase 2).

Harvested by demand: the corpus has ~10 game-theoretic models (prisoner's
dilemma, public goods, hawk-dove, Braess) and the payoff matrix is exactly what
`RuleTable` CANNOT represent — a payoff is ORDERED (a strategy-a player's payoff
against b differs from b's against a) and DUAL-output. The Coverage Gate would
false-cover it via lookup_table→RuleTable; this is the real operator for it.

The high-leverage point is COMPOSITION: PayoffGame × MoranProcess = evolutionary
game theory. Each generation agents play, accumulate payoff (= fitness), then
fitness-proportional turnover. Two operators, a whole research area.

Library vs strategy: the matrix lookup, the asymmetric dual payoff, and
best-response are library; WHICH game and how agents pair up is the model's.
"""
from __future__ import annotations

from typing import Sequence


class PayoffGame:
    """A symmetric 2-player normal-form game. ``M[a][b]`` is the payoff to a
    player using strategy ``a`` against an opponent using strategy ``b`` (both
    players read the same matrix; symmetry is in the ROLES, not the entries —
    ``M[a][b] != M[b][a]`` in general).
    """

    def __init__(self, payoffs: Sequence[Sequence[float]]) -> None:
        rows = [list(map(float, r)) for r in payoffs]
        n = len(rows)
        if n < 2:
            raise ValueError(f"PayoffGame needs >= 2 strategies, got {n}")
        if any(len(r) != n for r in rows):
            raise ValueError("PayoffGame matrix must be square (n_strategies x n_strategies)")
        self._m = rows
        self.n_strategies = n

    # ── lookups ──────────────────────────────────────────────────────────────

    def payoff(self, a: int, b: int) -> float:
        """Payoff to a strategy-``a`` player meeting a strategy-``b`` player."""
        return self._m[a][b]

    def play(self, a: int, b: int) -> tuple[float, float]:
        """One encounter: returns (payoff to a, payoff to b). Ordered + dual —
        the property RuleTable cannot express."""
        return (self._m[a][b], self._m[b][a])

    def best_response(self, b: int) -> int:
        """The strategy with the highest payoff against opponent strategy ``b``."""
        col = [self._m[a][b] for a in range(self.n_strategies)]
        return max(range(self.n_strategies), key=lambda a: col[a])

    # ── named-game factories (the common cases) ────────────────────────────────

    @classmethod
    def from_matrix(cls, rows: Sequence[Sequence[float]]) -> "PayoffGame":
        return cls(rows)

    @classmethod
    def prisoners_dilemma(cls, T: float = 5, R: float = 3, P: float = 1, S: float = 0) -> "PayoffGame":
        """Strategies 0=Cooperate, 1=Defect. Requires T>R>P>S; defection is the
        dominant strategy though mutual cooperation (R) beats mutual defection (P)."""
        return cls([[R, S], [T, P]])

    @classmethod
    def hawk_dove(cls, V: float = 2, C: float = 4) -> "PayoffGame":
        """Strategies 0=Dove, 1=Hawk. ESS hawk fraction = V/C when V<C."""
        return cls([[V / 2, 0], [V, (V - C) / 2]])

    @classmethod
    def rock_paper_scissors(cls, win: float = 1, lose: float = -1, tie: float = 0) -> "PayoffGame":
        """Strategies 0=Rock, 1=Paper, 2=Scissors. Cyclic — no dominant strategy."""
        return cls([[tie, lose, win], [win, tie, lose], [lose, win, tie]])

    @classmethod
    def stag_hunt(cls, stag: float = 4, sucker: float = 0, hare: float = 3, hare_alt: float = 2) -> "PayoffGame":
        """Strategies 0=Stag, 1=Hare. Coordination game: two equilibria
        (stag,stag) and (hare,hare)."""
        return cls([[stag, sucker], [hare, hare_alt]])


def self_test() -> bool:
    """Library self-test: the ordered/dual payoff (what distinguishes this from a
    RuleTable), the dominant strategy in PD, and the cyclic best-response in RPS.
    """
    pd = PayoffGame.prisoners_dilemma()          # 0=C 1=D, M=[[3,0],[5,1]]
    # ordered + dual: C-vs-D pays the cooperator S=0 and the defector T=5
    if pd.play(0, 1) != (0.0, 5.0):
        return False
    if pd.payoff(0, 1) == pd.payoff(1, 0):       # 0 != 5 — NOT order-free
        return False
    if pd.best_response(0) != 1 or pd.best_response(1) != 1:   # defect dominates
        return False

    rps = PayoffGame.rock_paper_scissors()       # 0=R 1=P 2=S
    if (rps.best_response(0), rps.best_response(1), rps.best_response(2)) != (1, 2, 0):
        return False                             # paper>rock, scissors>paper, rock>scissors

    try:
        PayoffGame([[1, 2, 3], [4, 5, 6]])       # non-square must reject
        return False
    except ValueError:
        pass
    return True
