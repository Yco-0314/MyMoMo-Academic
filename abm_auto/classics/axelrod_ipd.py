"""Axelrod (1984) IPD computer tournament — a faithful agent-based reproduction.

Source: Axelrod, R. (1984) *The Evolution of Cooperation*, Basic Books. The
round-robin "computer tournament" in which entrants (strategies) each play every
other entrant — and themselves — in the iterated Prisoner's Dilemma, scored by
total points, with TIT-FOR-TAT the winner.

Rules (verified against the canonical description):
  * Round-robin: every strategy plays EVERY strategy, INCLUDING ITSELF, in a
    head-to-head match of ``rounds`` (default 200) iterated PD rounds.
  * Payoffs (Axelrod's): T=5 (defect vs cooperate), R=3 (mutual cooperate),
    P=1 (mutual defect), S=0 (cooperate vs defect). T > R > P > S and
    2R > T + S, the standard PD ordering.
  * Each round, BOTH players choose C or D SIMULTANEOUSLY from the local match
    history (their own past moves + the opponent's past moves) — a genuine
    per-round decision, never a precomputed sequence. Each side's score for the
    round is read from the payoff matrix.
  * Score = total points a strategy accumulates across all of its matches
    (including the self-play match). Strategies are then ranked by total score.

GENUINE AGENT-BASED: each entrant is a ``StrategyAgent`` (subclass of the neutral
platform ``Agent``). Its ``decide(history)`` is the agent's policy; a ``Match``
asks the two agents to decide each round given the round-so-far history, then
records the moves. The model (``TournamentModel``) owns the round-robin schedule
and the score table. No god-loop hand-rolls the agents' decisions.

Strategy pool (8 canonical strategies):
  - TitForTat        — C first; thereafter copy the opponent's last move. NICE.
  - AllD             — always defect.
  - AllC             — always cooperate. NICE.
  - Random(p=0.5)    — C with prob p each round (seeded). non-nice.
  - Grudger / Grim   — C until the opponent defects once, then AllD forever. NICE.
  - TitForTwoTats    — C unless the opponent defected on BOTH of the last two
                       rounds (defect only after two consecutive defections). NICE.
  - SuspiciousTFT    — D first (Joss-like opening); thereafter copy opp last. non-nice.
  - Pavlov (WSLS)    — C first; then win-stay-lose-shift: repeat last move if last
                       round's payoff was a "win" (T or R), else switch. NICE (C first).

"NICE" = never the first to defect. By this definition the nice set is
{TitForTat, AllC, Grudger, TitForTwoTats, Pavlov}; the non-nice set is
{AllD, Random, SuspiciousTFT}.

Determinism: the only stochastic strategy is ``Random``. It draws from a
``random.Random`` seeded per match (``base_seed`` combined with the match index),
so a whole tournament is reproducible from one integer seed.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent

COOPERATE = "C"
DEFECT = "D"

# Axelrod's payoff matrix (my move, opponent move) -> my points.
T, R, P, S = 5, 3, 1, 0
PAYOFF: Dict[Tuple[str, str], int] = {
    (COOPERATE, COOPERATE): R,   # mutual cooperation
    (COOPERATE, DEFECT): S,      # I cooperate, sucker
    (DEFECT, COOPERATE): T,      # I defect on a cooperator (temptation)
    (DEFECT, DEFECT): P,         # mutual defection
}
# A "win" for win-stay-lose-shift (Pavlov): my move earned T or R this round.
_WIN_PAYOFFS = frozenset({T, R})


# -- Strategy agents -----------------------------------------------------------

class StrategyAgent(Agent):
    """One tournament entrant. Override ``decide`` to return C or D for the next
    round given this match's history so far.

    ``my_moves`` / ``opp_moves`` are the move lists for the CURRENT match (cleared
    by ``reset_match`` before each new head-to-head). ``name`` is the strategy
    label; ``nice`` flags whether the strategy is never the first to defect."""

    name: str = "Strategy"
    nice: bool = False

    def __init__(self, agent_id: int, model: Optional[Any] = None) -> None:
        super().__init__(agent_id, model)
        self.my_moves: List[str] = []
        self.opp_moves: List[str] = []

    def reset_match(self) -> None:
        """Clear local match memory before a new head-to-head match."""
        self.my_moves = []
        self.opp_moves = []

    def decide(self) -> str:  # pragma: no cover - overridden
        """Return COOPERATE or DEFECT for the next round, from local history."""
        raise NotImplementedError

    def record(self, my_move: str, opp_move: str) -> None:
        """Append this round's moves to the local match history."""
        self.my_moves.append(my_move)
        self.opp_moves.append(opp_move)


class TitForTat(StrategyAgent):
    name = "TitForTat"
    nice = True

    def decide(self) -> str:
        if not self.opp_moves:
            return COOPERATE          # nice opening
        return self.opp_moves[-1]      # copy opponent's last move


class AllD(StrategyAgent):
    name = "AllD"
    nice = False

    def decide(self) -> str:
        return DEFECT


class AllC(StrategyAgent):
    name = "AllC"
    nice = True

    def decide(self) -> str:
        return COOPERATE


class RandomStrategy(StrategyAgent):
    """Cooperate with probability ``p`` each round, from a seeded RNG."""
    name = "Random"
    nice = False

    def __init__(self, agent_id: int, model: Optional[Any] = None, *,
                 p: float = 0.5, rng: Optional[random.Random] = None) -> None:
        super().__init__(agent_id, model)
        self.p = p
        self.rng = rng or random.Random(0)

    def decide(self) -> str:
        return COOPERATE if self.rng.random() < self.p else DEFECT


class Grudger(StrategyAgent):
    """Grim trigger: cooperate until the opponent defects once, then defect forever."""
    name = "Grudger"
    nice = True

    def decide(self) -> str:
        if DEFECT in self.opp_moves:
            return DEFECT
        return COOPERATE


class TitForTwoTats(StrategyAgent):
    """Defect only after the opponent has defected on the last TWO rounds."""
    name = "TitForTwoTats"
    nice = True

    def decide(self) -> str:
        if len(self.opp_moves) >= 2 and self.opp_moves[-1] == DEFECT \
                and self.opp_moves[-2] == DEFECT:
            return DEFECT
        return COOPERATE


class SuspiciousTFT(StrategyAgent):
    """Suspicious / Joss-like TFT: DEFECT on the first move, then copy opp last."""
    name = "SuspiciousTFT"
    nice = False

    def decide(self) -> str:
        if not self.opp_moves:
            return DEFECT             # suspicious opening
        return self.opp_moves[-1]


class Pavlov(StrategyAgent):
    """Win-stay, lose-shift. Cooperate first; thereafter repeat the last move if
    last round's payoff was a "win" (T or R), else switch to the other move."""
    name = "Pavlov"
    nice = True

    def decide(self) -> str:
        if not self.my_moves:
            return COOPERATE          # nice opening
        last_mine = self.my_moves[-1]
        last_opp = self.opp_moves[-1]
        last_payoff = PAYOFF[(last_mine, last_opp)]
        if last_payoff in _WIN_PAYOFFS:
            return last_mine          # stay
        return DEFECT if last_mine == COOPERATE else COOPERATE  # shift


# Canonical pool factory order — FIXED before running; do NOT add/remove to
# engineer a ranking. Each entry is (class, kwargs) so Random can carry its seed.
STRATEGY_FACTORIES: Tuple[Tuple[type, dict], ...] = (
    (TitForTat, {}),
    (AllD, {}),
    (AllC, {}),
    (RandomStrategy, {"p": 0.5}),
    (Grudger, {}),
    (TitForTwoTats, {}),
    (SuspiciousTFT, {}),
    (Pavlov, {}),
)

NICE_STRATEGIES = frozenset(
    {"TitForTat", "AllC", "Grudger", "TitForTwoTats", "Pavlov"}
)


# -- Match ---------------------------------------------------------------------

class Match:
    """One head-to-head iterated-PD match between two ``StrategyAgent``s.

    Each round both agents decide SIMULTANEOUSLY from the round-so-far history,
    the payoff matrix scores both, and the moves are recorded into each agent's
    local history (so the NEXT round's decisions see them). Returns the two total
    scores. The same ``StrategyAgent`` instance can play several matches: call
    ``reset_match`` (done here) before each."""

    def __init__(self, a: StrategyAgent, b: StrategyAgent, *, rounds: int = 200) -> None:
        self.a = a
        self.b = b
        self.rounds = rounds

    def play(self) -> Tuple[int, int]:
        a, b = self.a, self.b
        a.reset_match()
        b.reset_match()
        score_a = 0
        score_b = 0
        for _ in range(self.rounds):
            move_a = a.decide()           # both decide from history-so-far
            move_b = b.decide()           # (simultaneous: neither sees the other's
            score_a += PAYOFF[(move_a, move_b)]   # current-round move)
            score_b += PAYOFF[(move_b, move_a)]
            a.record(move_a, move_b)      # commit to local history for next round
            b.record(move_b, move_a)
        return score_a, score_b


# -- Tournament model ----------------------------------------------------------

class TournamentModel:
    """Round-robin IPD tournament over a fixed strategy pool.

    Every strategy plays every strategy INCLUDING ITSELF over ``rounds`` rounds.
    For self-play a strategy needs two independent agent instances (so each keeps
    its own history); both copies' scores are added to that strategy's total. The
    model owns the schedule + the score table — it is the agent-based platform's
    model role for a non-spatial, match-structured ABM.

    ``seed`` seeds the per-match RNG for the Random strategy: match m uses
    ``random.Random(seed * 1_000_003 + m)`` so a whole tournament is reproducible
    and two seeds give independent Random play."""

    def __init__(self, *, rounds: int = 200, seed: int = 0,
                 factories: Tuple[Tuple[type, dict], ...] = STRATEGY_FACTORIES) -> None:
        self.rounds = rounds
        self.seed = seed
        self.factories = factories
        self.names: List[str] = [cls.name for cls, _ in factories]
        self.scores: Dict[str, int] = {name: 0 for name in self.names}
        # per-pairing breakdown: (name_i, name_j) -> (score_i, score_j)
        self.pair_scores: Dict[Tuple[str, str], Tuple[int, int]] = {}
        self._match_index = 0

    def _make_agent(self, idx: int, rng: random.Random) -> StrategyAgent:
        cls, kwargs = self.factories[idx]
        if cls is RandomStrategy:
            return cls(idx, self, rng=rng, **kwargs)  # type: ignore[arg-type]
        return cls(idx, self, **kwargs)

    def _match_rng(self) -> random.Random:
        rng = random.Random(self.seed * 1_000_003 + self._match_index)
        self._match_index += 1
        return rng

    def run(self) -> Dict[str, Any]:
        n = len(self.factories)
        for i in range(n):
            for j in range(i, n):          # i==j => self-play (incl. itself)
                rng_i = self._match_rng()
                rng_j = self._match_rng()
                ai = self._make_agent(i, rng_i)
                aj = self._make_agent(j, rng_j)
                si, sj = Match(ai, aj, rounds=self.rounds).play()
                self.scores[self.names[i]] += si
                self.scores[self.names[j]] += sj
                self.pair_scores[(self.names[i], self.names[j])] = (si, sj)
        ranking = self.ranking()
        return {
            "rounds": self.rounds,
            "seed": self.seed,
            "payoffs": {"T": T, "R": R, "P": P, "S": S},
            "pool": list(self.names),
            "scores": dict(self.scores),
            "ranking": ranking,
            "pair_scores": {f"{a}_vs_{b}": list(v)
                            for (a, b), v in self.pair_scores.items()},
        }

    def ranking(self) -> List[Dict[str, Any]]:
        """Strategies ranked by total score (desc). Ties share the metric; rank is
        the 1-based competition rank (1,2,2,4 style). Order within a tie is by name
        for determinism."""
        ordered = sorted(self.scores.items(), key=lambda kv: (-kv[1], kv[0]))
        out: List[Dict[str, Any]] = []
        last_score: Optional[int] = None
        last_rank = 0
        for pos, (name, score) in enumerate(ordered, start=1):
            if score != last_score:
                last_rank = pos
                last_score = score
            out.append({"rank": last_rank, "name": name, "score": score,
                        "nice": name in NICE_STRATEGIES})
        return out


# -- Multi-seed runner ---------------------------------------------------------

def run_tournament(*, rounds: int = 200, seed: int = 0,
                   factories: Tuple[Tuple[type, dict], ...] = STRATEGY_FACTORIES) -> Dict[str, Any]:
    """Run a single tournament at one seed; return its result dict."""
    return TournamentModel(rounds=rounds, seed=seed, factories=factories).run()


def run_many_seeds(*, rounds: int = 200, seeds: Tuple[int, ...] = (0, 1, 2, 3, 4),
                   factories: Tuple[Tuple[type, dict], ...] = STRATEGY_FACTORIES
                   ) -> Dict[str, Any]:
    """Run the tournament across several seeds (only the Random strategy is
    stochastic). Report per-seed scores + the mean score per strategy, then RANK
    by the mean total score (the LOCKED metric) with variance (min/max/stdev).

    Aggregating over seeds is the discipline guard (the design's coord-lesson):
    a Random-RNG fluctuation cannot masquerade as a ranking result."""
    names = [cls.name for cls, _ in factories]
    per_seed: List[Dict[str, Any]] = []
    sums: Dict[str, int] = {nm: 0 for nm in names}
    by_strategy: Dict[str, List[int]] = {nm: [] for nm in names}
    for s in seeds:
        res = TournamentModel(rounds=rounds, seed=s, factories=factories).run()
        per_seed.append({"seed": s, "scores": res["scores"], "ranking": res["ranking"]})
        for nm in names:
            sums[nm] += res["scores"][nm]
            by_strategy[nm].append(res["scores"][nm])
    n = len(seeds)
    mean_scores = {nm: sums[nm] / n for nm in names}

    def _stdev(xs: List[int]) -> float:
        if len(xs) < 2:
            return 0.0
        mu = sum(xs) / len(xs)
        return (sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5

    ordered = sorted(mean_scores.items(), key=lambda kv: (-kv[1], kv[0]))
    ranking: List[Dict[str, Any]] = []
    last_score: Optional[float] = None
    last_rank = 0
    for pos, (nm, ms) in enumerate(ordered, start=1):
        if last_score is None or abs(ms - last_score) > 1e-9:
            last_rank = pos
            last_score = ms
        xs = by_strategy[nm]
        ranking.append({
            "rank": last_rank, "name": nm,
            "mean_score": ms, "min_score": min(xs), "max_score": max(xs),
            "stdev": _stdev(xs), "nice": nm in NICE_STRATEGIES,
        })
    return {
        "rounds": rounds, "seeds": list(seeds),
        "payoffs": {"T": T, "R": R, "P": P, "S": S},
        "pool": names,
        "per_seed": per_seed,
        "mean_scores": mean_scores,
        "ranking": ranking,
    }


# -- Metric helpers (the LOCKED grading metric: total-score ranking) -----------

def rank_of(ranking: List[Dict[str, Any]], name: str) -> int:
    """1-based rank of ``name`` in a ranking list (from run_many_seeds/ranking)."""
    for row in ranking:
        if row["name"] == name:
            return row["rank"]
    raise KeyError(name)


def top_score(ranking: List[Dict[str, Any]]) -> float:
    """The top (rank-1) mean score in a ranking list."""
    key = "mean_score" if "mean_score" in ranking[0] else "score"
    return max(row[key] for row in ranking)


def mean_rank(ranking: List[Dict[str, Any]], names) -> float:
    """Mean rank of a set of strategy names (lower = better)."""
    names = set(names)
    rows = [row["rank"] for row in ranking if row["name"] in names]
    return sum(rows) / len(rows) if rows else float("nan")
