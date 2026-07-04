"""Win-Stay-Lose-Shift (Pavlov) in the NOISY iterated PD — a faithful agent-based
reproduction of Nowak & Sigmund (1993).

Source: Nowak, M. & Sigmund, K. (1993), "A strategy of win-stay, lose-shift that
outperforms tit-for-tat in the Prisoner's Dilemma game", Nature 364:56-58.
doi:10.1038/364056a0.

The claim reproduced here is emphatically NOT the noise-free deterministic Axelrod
round-robin (``abm_auto.classics.axelrod_ipd``), where TIT-FOR-TAT wins. It is a
different regime — a NOISY, EVOLVING population — in which win-stay-lose-shift (WSLS,
"Pavlov") outcompetes TFT because of two mechanisms that only bite under noise +
selection:

  * ERROR-CORRECTION under noise. Two TFT players, hit by an implementation error, fall
    into a long alternating echo of retaliations (CD, DC, CD, ...) that noise keeps
    re-igniting, so TFT self-play is eroded. Two WSLS players, after an accidental
    defection, land in mutual defection (a "lose"), both shift, and RESTORE cooperation
    within a couple of rounds. WSLS self-play is self-repairing; TFT self-play is not.
  * EXPLOITATION of unconditional cooperators. Against ALLC, WSLS learns to defect and
    STAY (defecting on a cooperator is a "win", T), harvesting T every round, whereas
    TFT keeps cooperating with a cooperator and only ever collects R. WSLS is not "nice"
    in the Axelrod sense — it exploits suckers — and that is exactly why it wins the
    evolutionary game once ALLC drifts in.

Model — memory-one strategies in the noisy IPD
----------------------------------------------
A memory-one (reactive-with-own-move) strategy is a 4-vector

    p = (p_R, p_S, p_T, p_P)

giving the probability of playing C on the NEXT round as a function of the LAST round's
OUTCOME for this player: R (both cooperated), S (I cooperated, sucker), T (I defected on
a cooperator, temptation), P (both defected). The four canonical strategies are:

    WSLS / Pavlov = (1, 0, 0, 1)   # C after R or P (repeat if it "worked"); D after S or T
    TFT           = (1, 0, 1, 0)   # play what the OPPONENT just played (C after R/T, D after S/P)
    ALLC          = (1, 1, 1, 1)
    ALLD          = (0, 0, 0, 0)

(WSLS reads as win-stay-lose-shift: after a "win" R or T repeat last move — but note the
memory-one form is stated in terms of the *cooperation* probability, so WSLS = C after R
and after P. After R you cooperated and won, so cooperate again; after P you defected and
that was a "loss", so shift to C. That is precisely (p_R,p_S,p_T,p_P)=(1,0,0,1). Likewise
TFT copies the opponent: after R/T the opponent played C so play C; after S/P the opponent
played D so play D → (1,0,1,0).)

Implementation NOISE ε: the *intended* move (the memory-one draw) is flipped to the other
action with probability ε on every move. ε >= 0.01. Noise is what makes the reactive
strategies' behaviour differ from the deterministic tournament — it is the load-bearing
ingredient of the whole result.

Payoffs (canonical PD, T>R>P>S with 2R>T+S): T=5, R=3, P=1, S=0. The pairwise score is
the MEAN per-round payoff over the interaction.

Exact pairwise payoff via the memory-one Markov chain
-----------------------------------------------------
Two memory-one strategies playing each other with noise define a Markov chain over the
four JOINT states (my move, opp move) ∈ {CC, CD, DC, DD}. From a joint state, each player
independently computes its intended next move from its own outcome, then flips it with
probability ε. The 4×4 transition matrix is exact; its unique stationary distribution π
gives the exact long-run frequency of each joint outcome, and the mean per-round payoff is
Σ_state π(state) · payoff(state). Noise (ε>0) makes the chain irreducible + aperiodic, so
π is unique and the fixed point is reached by power-iteration to convergence. This is the
"exact, fast" route named in the spec; a many-round noisy SIMULATION agrees with it (a
test cross-checks the two).

GENUINE AGENT-BASED. Each strategy is a ``MemoryOneAgent`` (subclass of the neutral
platform ``Agent``) carrying its 4-vector policy; ``intended_move(my_last, opp_last)`` is
the agent's own policy draw and ``noisy_move`` applies the implementation error. A
``NoisyMatch`` asks the two agents to move each round from the local last-round outcome —
a genuine per-round agent decision, never a precomputed sequence. The evolutionary
``EvolvingPopulation`` (P3) is a finite population of agents each CARRYING a strategy
label; each generation it computes mean-field payoffs, reproduces proportionally
(replicator with a finite ~100 population, so drift is real), and mutates. No god-loop
hand-rolls the agents' choices.

Evolution (P3): a finite population of ``PopMember`` agents, each holding one strategy
from {WSLS, TFT, ALLC, ALLD}. Each generation: (1) every strategy's fitness = mean pairwise
payoff against the current population mixture (well-mixed, self-interaction included via the
exact Markov payoff); (2) the next generation is drawn by fitness-proportional selection
(finite N → sampling drift, seeded); (3) each offspring mutates to a uniformly-random
strategy with probability μ. Run to a late window over ≥10 seeds. An INVASION control seeds
a resident population (all-WSLS or all-TFT) with a small ALLC minority and asks whether ALLC
grows: WSLS punishes the ALLC drifters (exploits + resists) whereas a TFT resident, being
exploited-neutral toward cooperators, lets ALLC accumulate.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

COOPERATE = "C"
DEFECT = "D"

# Canonical PD payoff matrix (my move, opp move) -> my points; T>R>P>S, 2R>T+S.
T, R, P, S = 5.0, 3.0, 1.0, 0.0
PAYOFF: Dict[Tuple[str, str], float] = {
    (COOPERATE, COOPERATE): R,   # both cooperate
    (COOPERATE, DEFECT): S,      # I cooperate, sucker
    (DEFECT, COOPERATE): T,      # I defect on a cooperator (temptation)
    (DEFECT, DEFECT): P,         # both defect
}

# The four joint states (my move, opp move), in a FIXED order.
JOINT_STATES: Tuple[Tuple[str, str], ...] = (
    (COOPERATE, COOPERATE),   # CC
    (COOPERATE, DEFECT),      # CD  (I cooperate, opp defects -> my outcome S)
    (DEFECT, COOPERATE),      # DC  (I defect, opp cooperates -> my outcome T)
    (DEFECT, DEFECT),         # DD
)

# Memory-one policy vectors (p_R, p_S, p_T, p_P) = P(play C next | my last-round outcome).
# Named strategy library — FIXED before running; do NOT retune these vectors.
STRATEGIES: Dict[str, Tuple[float, float, float, float]] = {
    "WSLS": (1.0, 0.0, 0.0, 1.0),   # Pavlov: C after R or P, D after S or T
    "TFT":  (1.0, 0.0, 1.0, 0.0),   # copy opponent: C after R or T, D after S or P
    "ALLC": (1.0, 1.0, 1.0, 1.0),
    "ALLD": (0.0, 0.0, 0.0, 0.0),
}


def _my_outcome(my_move: str, opp_move: str) -> str:
    """The last-round OUTCOME label (R/S/T/P) for the player who made ``my_move`` against
    ``opp_move``. This is the index a memory-one strategy reacts to."""
    if my_move == COOPERATE and opp_move == COOPERATE:
        return "R"
    if my_move == COOPERATE and opp_move == DEFECT:
        return "S"
    if my_move == DEFECT and opp_move == COOPERATE:
        return "T"
    return "P"


_OUTCOME_INDEX = {"R": 0, "S": 1, "T": 2, "P": 3}


def coop_prob(policy: Sequence[float], my_move: str, opp_move: str) -> float:
    """P(this player plays C next round) under ``policy`` given last round's (my, opp)
    moves — i.e. index the 4-vector by this player's last-round outcome R/S/T/P."""
    return policy[_OUTCOME_INDEX[_my_outcome(my_move, opp_move)]]


# ── Agent ─────────────────────────────────────────────────────────────────────

class MemoryOneAgent(Agent):
    """One player carrying a memory-one policy vector ``(p_R, p_S, p_T, p_P)`` plus the
    implementation-noise level ε.

    ``intended_move`` is the agent's own policy draw from the last-round outcome (or the
    fixed opening on the first move); ``noisy_move`` flips that intended action to the
    other one with probability ε (the implementation error). Both consume the agent's RNG
    so a match is reproducible from a seed. The per-agent ``step`` is a no-op: a round is
    driven by the match, which asks both agents to move from the shared last-round state.
    """

    def __init__(self, agent_id: int, model: Optional[Any] = None, *,
                 policy: Sequence[float], name: str = "memory-one", eps: float = 0.01,
                 open_move: str = COOPERATE, rng: Optional[random.Random] = None) -> None:
        super().__init__(agent_id, model)
        if len(policy) != 4:
            raise ValueError(f"policy must be a 4-vector (p_R,p_S,p_T,p_P); got {policy!r}")
        if not (0.0 <= eps <= 1.0):
            raise ValueError(f"eps must be in [0,1]; got {eps}")
        self.policy = tuple(float(x) for x in policy)
        self.name = name
        self.eps = float(eps)
        self.open_move = open_move
        self.rng = rng or random.Random(0)

    def intended_move(self, my_last: Optional[str], opp_last: Optional[str]) -> str:
        """The agent's INTENDED action (before implementation noise): the fixed opening on
        the first round, else a C/D draw from the memory-one policy applied to last round's
        outcome."""
        if my_last is None or opp_last is None:
            return self.open_move
        p_c = coop_prob(self.policy, my_last, opp_last)
        return COOPERATE if self.rng.random() < p_c else DEFECT

    def noisy_move(self, my_last: Optional[str], opp_last: Optional[str]) -> str:
        """The REALISED action = intended action flipped with probability ε (the
        implementation error / trembling hand)."""
        move = self.intended_move(my_last, opp_last)
        if self.rng.random() < self.eps:
            return DEFECT if move == COOPERATE else COOPERATE
        return move

    def step(self) -> None:  # pragma: no cover - a round lives on the match
        """A round is a match-level interaction (both agents move from the shared
        last-round outcome), not an autonomous single-agent step."""
        return None


# ── Exact pairwise payoff via the memory-one Markov chain ──────────────────────

def transition_matrix(policy_a: Sequence[float], policy_b: Sequence[float],
                      eps: float) -> List[List[float]]:
    """4×4 row-stochastic transition matrix over the joint states
    (my=a's move, opp=b's move) ∈ {CC, CD, DC, DD} for two memory-one players a, b under
    implementation noise ε.

    From a joint state, player a computes P(a plays C) from a's own last outcome and
    player b computes P(b plays C) from b's own last outcome (b's moves are the mirror,
    so b's outcome uses (b_move, a_move)); each intended action is then flipped w.p. ε.
    The two players' realised moves are INDEPENDENT given the state, so the joint next-state
    probability is the product of the two per-player realised-C probabilities."""
    def realised_c_prob(p_intended_c: float) -> float:
        # P(realised C) = P(intended C)·(1-ε) + P(intended D)·ε
        return p_intended_c * (1.0 - eps) + (1.0 - p_intended_c) * eps

    mat: List[List[float]] = []
    for (a_move, b_move) in JOINT_STATES:
        # a reacts to a's outcome (a_move vs b_move); b reacts to b's outcome (b_move vs a_move).
        pa_int_c = coop_prob(policy_a, a_move, b_move)
        pb_int_c = coop_prob(policy_b, b_move, a_move)
        pa_c = realised_c_prob(pa_int_c)
        pb_c = realised_c_prob(pb_int_c)
        row = [
            pa_c * pb_c,               # -> CC
            pa_c * (1.0 - pb_c),       # -> CD
            (1.0 - pa_c) * pb_c,       # -> DC
            (1.0 - pa_c) * (1.0 - pb_c),  # -> DD
        ]
        mat.append(row)
    return mat


def stationary_distribution(mat: Sequence[Sequence[float]], *,
                            max_iter: int = 100_000, tol: float = 1e-14) -> List[float]:
    """Unique stationary distribution π (πP = π) of a row-stochastic 4×4 matrix, by power
    iteration from the uniform start. With ε>0 the chain is irreducible + aperiodic, so π
    is unique and iteration converges. Returns a length-4 probability vector."""
    n = len(mat)
    pi = [1.0 / n] * n
    for _ in range(max_iter):
        nxt = [0.0] * n
        for i in range(n):
            pi_i = pi[i]
            if pi_i == 0.0:
                continue
            row = mat[i]
            for j in range(n):
                nxt[j] += pi_i * row[j]
        diff = sum(abs(nxt[j] - pi[j]) for j in range(n))
        pi = nxt
        if diff < tol:
            break
    total = sum(pi)
    return [x / total for x in pi] if total > 0 else pi


def exact_payoffs(policy_a: Sequence[float], policy_b: Sequence[float], eps: float,
                  ) -> Tuple[float, float]:
    """Exact long-run mean per-round payoffs (a's, b's) for two memory-one strategies under
    noise ε, via the joint-state stationary distribution. a's payoff reads the PAYOFF for
    (a_move, b_move); b's payoff reads the mirror (b_move, a_move)."""
    if not (0.0 < eps < 1.0):
        # ε must be strictly interior for the chain to be irreducible; the study uses
        # ε=0.01, but guard so a caller cannot silently get a degenerate chain.
        if eps <= 0.0:
            raise ValueError("exact_payoffs needs eps > 0 (noise makes the chain ergodic)")
        raise ValueError("exact_payoffs needs eps < 1")
    mat = transition_matrix(policy_a, policy_b, eps)
    pi = stationary_distribution(mat)
    pay_a = 0.0
    pay_b = 0.0
    for prob, (a_move, b_move) in zip(pi, JOINT_STATES):
        pay_a += prob * PAYOFF[(a_move, b_move)]
        pay_b += prob * PAYOFF[(b_move, a_move)]
    return pay_a, pay_b


def exact_payoff(name_a: str, name_b: str, eps: float) -> Tuple[float, float]:
    """Exact mean per-round payoffs (a, b) for two NAMED strategies at noise ε."""
    return exact_payoffs(STRATEGIES[name_a], STRATEGIES[name_b], eps)


# ── Many-round noisy simulation (agent-based cross-check of the exact chain) ────

class NoisyMatch:
    """One head-to-head noisy IPD match between two ``MemoryOneAgent``s over ``rounds``
    rounds. Each round both agents realise a move from the shared last-round outcome (their
    own last move + the opponent's last move) with implementation noise; the payoff matrix
    scores both. Returns the two MEAN per-round payoffs. This is the genuine agent-based
    path; ``exact_payoffs`` is its analytic limit as rounds→∞."""

    def __init__(self, a: MemoryOneAgent, b: MemoryOneAgent, *, rounds: int = 100_000) -> None:
        self.a = a
        self.b = b
        self.rounds = rounds

    def play(self) -> Tuple[float, float]:
        a, b = self.a, self.b
        a_last: Optional[str] = None
        b_last: Optional[str] = None
        total_a = 0.0
        total_b = 0.0
        for _ in range(self.rounds):
            move_a = a.noisy_move(a_last, b_last)   # a's outcome-index is (a_last, b_last)
            move_b = b.noisy_move(b_last, a_last)   # b's outcome-index is (b_last, a_last)
            total_a += PAYOFF[(move_a, move_b)]
            total_b += PAYOFF[(move_b, move_a)]
            a_last, b_last = move_a, move_b
        return total_a / self.rounds, total_b / self.rounds


def simulate_payoffs(name_a: str, name_b: str, eps: float, *, rounds: int = 200_000,
                     seed: int = 0) -> Tuple[float, float]:
    """Agent-based noisy simulation of the mean per-round payoffs for two named strategies.
    Two independent seeded RNGs (one per agent) so self-play uses distinct trembles."""
    a = MemoryOneAgent(0, None, policy=STRATEGIES[name_a], name=name_a, eps=eps,
                       rng=random.Random(seed * 2 + 1))
    b = MemoryOneAgent(1, None, policy=STRATEGIES[name_b], name=name_b, eps=eps,
                       rng=random.Random(seed * 2 + 2))
    return NoisyMatch(a, b, rounds=rounds).play()


# ── Evolutionary population (P3) ───────────────────────────────────────────────

class PopMember(Agent):
    """One member of the evolving population, carrying a strategy label. The genuine
    agent unit of the evolutionary game: reproduction resamples these members by fitness
    and mutation flips a member's label."""

    def __init__(self, agent_id: int, model: Optional[Any] = None, *, strategy: str) -> None:
        super().__init__(agent_id, model)
        self.strategy = strategy

    def step(self) -> None:  # pragma: no cover - evolution is a model-level generation
        return None


class EvolvingPopulation(AgentModel):
    """A finite well-mixed population of ``PopMember`` agents evolving under
    fitness-proportional selection + mutation in the NOISY IPD.

    Each generation:
      1. FITNESS — every strategy's fitness is its mean pairwise exact-Markov payoff against
         the current population mixture (well-mixed; a member also meets its own type, so
         self-interaction is included by weighting by the strategy frequency). Payoffs are the
         exact noisy-IPD Markov payoffs at ε.
      2. SELECTION — the next generation of N members is drawn by fitness-proportional
         (roulette) sampling from the current strategy frequencies weighted by fitness.
         Finite N ⇒ genuine sampling DRIFT (seeded, reproducible).
      3. MUTATION — each offspring mutates to a uniformly-random strategy with probability μ.

    Records the per-generation frequency of every strategy. ``run(generations)`` advances
    and returns the full frequency trajectory; the late-window frequencies are the locked P3
    metric.
    """

    def __init__(self, *, strategies: Sequence[str] = ("WSLS", "TFT", "ALLC", "ALLD"),
                 n: int = 100, eps: float = 0.01, mu: float = 0.01,
                 init_counts: Optional[Dict[str, int]] = None, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if not (0.0 <= mu <= 1.0):
            raise ValueError(f"mu must be in [0,1]; got {mu}")
        self.strategy_names = list(strategies)
        self.n = n
        self.eps = float(eps)
        self.mu = float(mu)
        self.seed_value = seed

        # Precompute the exact pairwise payoff matrix over the strategy set (fixed given ε).
        self.payoff_matrix: Dict[Tuple[str, str], float] = {}
        for a in self.strategy_names:
            for b in self.strategy_names:
                pa, _ = exact_payoffs(STRATEGIES[a], STRATEGIES[b], self.eps)
                self.payoff_matrix[(a, b)] = pa

        # Initial roster: given counts, else uniform split (remainder to the first types).
        if init_counts is None:
            base = n // len(self.strategy_names)
            counts = {s: base for s in self.strategy_names}
            for i in range(n - base * len(self.strategy_names)):
                counts[self.strategy_names[i]] += 1
        else:
            counts = {s: int(init_counts.get(s, 0)) for s in self.strategy_names}
            if sum(counts.values()) != n:
                raise ValueError(
                    f"init_counts must sum to n={n}; got {sum(counts.values())}")
        self.members: List[PopMember] = []
        idx = 0
        for s in self.strategy_names:
            for _ in range(counts[s]):
                m = PopMember(idx, self, strategy=s)
                self.members.append(m)
                self.add_agent(m)
                idx += 1

        self.reporter = DataCollector({
            s: (lambda m, s=s: m.frequency(s)) for s in self.strategy_names
        })

    # -- population state --
    def counts(self) -> Dict[str, int]:
        c = {s: 0 for s in self.strategy_names}
        for m in self.members:
            c[m.strategy] += 1
        return c

    def frequency(self, name: str) -> float:
        return self.counts()[name] / self.n if self.n else 0.0

    def frequencies(self) -> Dict[str, float]:
        c = self.counts()
        return {s: c[s] / self.n for s in self.strategy_names}

    # -- one generation --
    def fitness(self, freqs: Dict[str, float]) -> Dict[str, float]:
        """Mean-field fitness of each strategy = expected exact payoff against a random
        opponent drawn from the current frequencies (self-interaction included via own
        frequency)."""
        fit: Dict[str, float] = {}
        for a in self.strategy_names:
            fit[a] = sum(freqs[b] * self.payoff_matrix[(a, b)]
                         for b in self.strategy_names)
        return fit

    def step(self) -> None:
        """One evolutionary generation: fitness → fitness-proportional resampling of N new
        members → mutation. Uses the model RNG so a run is reproducible from its seed."""
        freqs = self.frequencies()
        fit = self.fitness(freqs)
        # Fitness-proportional weight of each strategy in the mating pool = freq · fitness.
        # (PD payoffs are all > 0 here, so weights are non-negative and a positive strategy
        # frequency with positive fitness contributes.)
        weights = {s: freqs[s] * fit[s] for s in self.strategy_names}
        total_w = sum(weights.values())
        names = self.strategy_names
        if total_w <= 0.0:
            # degenerate (all-zero fitness) — keep the current mixture as the sampling base
            probs = [freqs[s] for s in names]
        else:
            probs = [weights[s] / total_w for s in names]

        new_members: List[PopMember] = []
        for idx in range(self.n):
            r = self.rng.random()
            cum = 0.0
            chosen = names[-1]
            for s, p in zip(names, probs):
                cum += p
                if r < cum:
                    chosen = s
                    break
            # mutation to a uniformly-random strategy
            if self.rng.random() < self.mu:
                chosen = names[self.rng.randrange(len(names))]
            new_members.append(PopMember(idx, self, strategy=chosen))

        self.members = new_members
        # rebuild the AgentSet roster so the model's agent collection tracks the new members
        self.agents = type(self.agents)([], schedule="sequential", rng=self.rng)
        for m in self.members:
            self.add_agent(m)
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, generations: int = 500, *, measure_last: int = 100) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``generations`` evolutionary generations; return the run summary with the
        per-generation frequency series for every strategy and the late-window (trailing
        ``measure_last``) mean frequency of each."""
        if measure_last <= 0 or measure_last > generations + 1:
            raise ValueError(
                f"measure_last must be in [1, generations+1] (got {measure_last}, "
                f"generations={generations})")
        self.reporter.collect(self)                      # gen 0 baseline
        for _ in range(generations):
            self.step()
        series = {s: self.reporter.series(s) for s in self.strategy_names}
        late = {s: tail_mean(series[s], window=measure_last) for s in self.strategy_names}
        return {
            "strategies": list(self.strategy_names),
            "n": self.n, "eps": self.eps, "mu": self.mu, "seed": self.seed_value,
            "generations": generations, "measure_last": measure_last,
            "freq_series": series,
            "late_freq": late,
            "final_freq": {s: series[s][-1] for s in self.strategy_names},
        }


# ── summary helpers ────────────────────────────────────────────────────────────

def tail_mean(series: Sequence[float], *, window: int = 100) -> float:
    """Steady-state estimate = mean of the trailing ``window`` of a series (whole series if
    shorter). Averaging the tail smooths finite-N drift + discards the transient."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_evolution(*, n: int = 100, eps: float = 0.01, mu: float = 0.01,
                  init_counts: Optional[Dict[str, int]] = None,
                  strategies: Sequence[str] = ("WSLS", "TFT", "ALLC", "ALLD"),
                  seed: int = 0, generations: int = 500,
                  measure_last: int = 100) -> Dict[str, Any]:
    """One evolutionary run at a given seed and the fixed noisy-IPD parameters."""
    return EvolvingPopulation(strategies=strategies, n=n, eps=eps, mu=mu,
                              init_counts=init_counts, seed=seed).run(
        generations, measure_last=measure_last)


def run_evolution_many_seeds(*, n: int = 100, eps: float = 0.01, mu: float = 0.01,
                             init_counts: Optional[Dict[str, int]] = None,
                             strategies: Sequence[str] = ("WSLS", "TFT", "ALLC", "ALLD"),
                             n_seeds: int = 10, seed_base: int = 0,
                             generations: int = 500,
                             measure_last: int = 100) -> Dict[str, Any]:
    """Run ``n_seeds`` evolutionary runs (seed ``seed_base + i``) at fixed parameters and
    summarise each strategy's late-window mean frequency across seeds (mean + spread).

    Aggregating over seeds is the discipline guard: a single finite-population drift
    fluctuation cannot masquerade as a dominance result."""
    runs = [run_evolution(n=n, eps=eps, mu=mu, init_counts=init_counts,
                          strategies=strategies, seed=seed_base + i,
                          generations=generations, measure_last=measure_last)
            for i in range(n_seeds)]
    names = list(strategies)
    per_seed_late = {s: [rr["late_freq"][s] for rr in runs] for s in names}
    mean_late = {s: sum(per_seed_late[s]) / n_seeds for s in names}

    def _std(xs: List[float]) -> float:
        if len(xs) < 2:
            return 0.0
        mu_x = sum(xs) / len(xs)
        return (sum((x - mu_x) ** 2 for x in xs) / len(xs)) ** 0.5

    return {
        "strategies": names,
        "n": n, "eps": eps, "mu": mu, "init_counts": init_counts,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "generations": generations, "measure_last": measure_last,
        "per_seed_late_freq": per_seed_late,
        "mean_late_freq": mean_late,
        "std_late_freq": {s: _std(per_seed_late[s]) for s in names},
        "min_late_freq": {s: min(per_seed_late[s]) for s in names},
        "max_late_freq": {s: max(per_seed_late[s]) for s in names},
        # one representative trajectory (first seed) for inspection.
        "example_freq_series": runs[0]["freq_series"],
    }


def invasion_test(*, resident: str, invader: str = "ALLC", invader_count: int = 5,
                  n: int = 100, eps: float = 0.01, mu: float = 0.0,
                  n_seeds: int = 10, seed_base: int = 0, generations: int = 300,
                  measure_last: int = 100) -> Dict[str, Any]:
    """Seed a ``resident``-strategy population with a small ``invader`` (default ALLC)
    minority and measure whether the invader GROWS. Mutation is OFF by default so the test
    isolates selection: does the resident RESIST (invader stays low / dies) or ADMIT (invader
    accumulates)? Two-strategy population so the outcome is a clean selection signal.

    Returns the mean (over seeds) late-window invader frequency; a resident that RESISTS
    keeps it below the seed level, a resident that ADMITS lets it rise."""
    strategies = (resident, invader)
    init_counts = {resident: n - invader_count, invader: invader_count}
    init_freq = invader_count / n
    res = run_evolution_many_seeds(
        n=n, eps=eps, mu=mu, init_counts=init_counts, strategies=strategies,
        n_seeds=n_seeds, seed_base=seed_base, generations=generations,
        measure_last=measure_last)
    return {
        "resident": resident, "invader": invader,
        "init_invader_count": invader_count, "init_invader_freq": init_freq,
        "n": n, "eps": eps, "mu": mu, "n_seeds": n_seeds,
        "generations": generations, "measure_last": measure_last,
        "mean_late_invader_freq": res["mean_late_freq"][invader],
        "std_late_invader_freq": res["std_late_freq"][invader],
        "per_seed_late_invader_freq": res["per_seed_late_freq"][invader],
        "mean_late_resident_freq": res["mean_late_freq"][resident],
        "example_freq_series": res["example_freq_series"],
    }
