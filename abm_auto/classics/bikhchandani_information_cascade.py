"""Bikhchandani-Hirshleifer-Welch (1992) informational cascade — a faithful
agent-based reproduction (the canonical follow-own-signal model).

Source: Bikhchandani, S., Hirshleifer, D. & Welch, I. (1992), "A Theory of Fads,
Fashion, Custom, and Cultural Change as Informational Cascades", Journal of
Political Economy 100(5):992-1026. doi:10.1086/261849.

The model — a queue of rational Bayesian agents acting once each, in order:

  * A hidden binary world state theta in {H, L}, prior P(H)=1/2. It is fixed for
    the whole queue (the "true" state the agents are trying to match).
  * N agents act ONCE each in a fixed order 1..N. Before acting, agent i draws a
    conditionally-independent private signal s_i in {h, l} of symmetric precision
    p = P(s=h | H) = P(s=l | L) > 1/2, and OBSERVES all predecessors' ACTIONS
    a_1..a_{i-1} (in {H, L}) — never their signals.
  * The agent Bayes-updates on (public actions + own signal) and takes the action
    with the higher posterior; a TIE (equal posterior) is broken by following one's
    own signal (the canonical convention). Reward is matching theta.

Why the decision collapses to an integer walk (and why cascades are exact):
Each PRE-cascade action perfectly reveals the actor's signal, because when the
public history is balanced or leads by one, a rational agent still follows its own
signal. So the public log-likelihood ratio from the history is proportional to the
net action difference d = (#H actions) - (#L actions), in units of the per-signal
weight w = ln(p/(1-p)). The agent's own signal contributes +w (high) or -w (low).
Hence the agent's posterior sign is the sign of (d + s) with s in {+1, -1}:

    d + s > 0  -> act H
    d + s < 0  -> act L
    d + s = 0  -> tie -> follow own signal (act H if s=+1, L if s=-1)

A CASCADE begins as soon as |d| reaches 2: then |d| > 1 >= |s| for any single
signal, so every subsequent agent rationally IGNORES its own signal and copies the
lead (herds) — d never changes again, and no further private information enters the
public record. Because d is a +-1 random walk absorbed at +-2 starting from 0, a
cascade forms in PAIRS from a balanced history: a fresh pair triggers a cascade with
probability p^2 + (1-p)^2 (both signals agree) and returns to balance with
probability 2p(1-p) (the two signals disagree). This is the mechanism; the closed
forms the experiment grades (P(no cascade after k pairs) = (2p(1-p))^k;
P(incorrect | cascade) = (1-p)^2 / (p^2 + (1-p)^2); E[agents before cascade] =
2 / (p^2 + (1-p)^2)) all follow from it.

Built on the neutral platform (``abm_auto._platform``): each agent is a
``CascadeAgent`` carrying its private signal and its chosen action; the model steps
the agents in queue order (a genuine sequential update), each reading only the public
action history via the model. Given a seed the whole queue is reproducible. A Monte
Carlo over many seeded queues estimates the cascade statistics, which are compared to
the closed forms above.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from abm_auto._platform import Agent, AgentModel

# Actions / states are the two symbols "H" and "L"; signals the lowercase "h"/"l".
HIGH = "H"
LOW = "L"


# -- Agent --------------------------------------------------------------------

class CascadeAgent(Agent):
    """One decision-maker in the queue.

    Carries its private ``signal`` in {"h", "l"} (drawn from the world state at the
    fixed precision p) and, once it acts, its chosen ``action`` in {"H", "L"}. The
    Bayes decision reads only the model's PUBLIC action tally (predecessors' actions),
    never any other agent's signal — that is the whole point of the model.
    """

    def __init__(self, agent_id: int, model: "CascadeModel", *, signal: str) -> None:
        super().__init__(agent_id, model)
        if signal not in ("h", "l"):
            raise ValueError(f"signal must be 'h' or 'l' (got {signal!r})")
        self.signal = signal
        self.action: Optional[str] = None
        # Whether this agent acted inside a cascade (ignored its own signal). Set by
        # ``decide`` for diagnostics; not consulted by any decision.
        self.in_cascade = False
        self.signal_revealed = False

    def decide(self, d: int) -> str:
        """Return this agent's rational action given the public net action difference
        ``d`` = (#H actions - #L actions) among predecessors.

        Posterior sign = sign(d + s) with s = +1 for a high signal, -1 for a low
        signal; a tie (d + s == 0) is broken by following one's own signal. Equivalent
        Bayesian statement: the public log-odds is d*ln(p/(1-p)), the signal adds
        +-ln(p/(1-p)), and p>1/2 makes the weight positive so only the SIGN of (d + s)
        matters.
        """
        s = 1 if self.signal == "h" else -1
        score = d + s
        if score > 0:
            act = HIGH
        elif score < 0:
            act = LOW
        else:  # tie -> follow own signal
            act = HIGH if s == 1 else LOW
        # Diagnostics: an agent is "in a cascade" iff the public lead alone already
        # determines its action regardless of its own signal (|d| >= 2). Then its
        # action does NOT reveal its signal.
        self.in_cascade = abs(d) >= 2
        self.signal_revealed = not self.in_cascade
        self.action = act
        return act

    def step(self) -> None:  # the model drives the ordered queue, not a sweep
        pass


# -- Model --------------------------------------------------------------------

class CascadeModel(AgentModel):
    """One realised BHW queue: a hidden state, N agents acting in order.

    Construct with N, the signal precision p, and a seed. ``run`` draws the hidden
    state (uniform prior), draws each agent's private signal from that state at
    precision p, then steps the agents in queue order — each Bayes-deciding from the
    running public action tally — and returns the queue summary: whether/where a
    cascade formed, its direction, whether it is correct, and how many agents acted on
    private information before it began.
    """

    def __init__(self, *, n: int = 30, p: float = 0.7, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n < 1:
            raise ValueError(f"n must be >= 1 (got {n})")
        if not (0.5 < p < 1.0):
            raise ValueError(f"precision p must be in (0.5, 1.0) (got {p})")
        self.n = n
        self.p = float(p)
        self.seed_value = seed

        # Hidden world state, uniform prior 1/2. Encoded as the "true" action label.
        self.true_state = HIGH if self.rng.random() < 0.5 else LOW

        # Each agent draws a private signal: correct (matches the state) w.p. p.
        # signal "h" points at H, "l" points at L.
        correct_symbol = "h" if self.true_state == HIGH else "l"
        wrong_symbol = "l" if self.true_state == HIGH else "h"
        self.agent_list: List[CascadeAgent] = []
        for i in range(n):
            sig = correct_symbol if self.rng.random() < self.p else wrong_symbol
            agent = CascadeAgent(i, self, signal=sig)
            self.agent_list.append(agent)
            self.add_agent(agent)

        # Public running tally, maintained as agents act. d = (#H - #L) among actions
        # taken so far. It is the ONLY thing a later agent reads about its predecessors
        # (their actions), never their signals.
        self.n_high = 0
        self.n_low = 0

    # -- public state --
    @property
    def d(self) -> int:
        """Net public action difference (#H actions - #L actions) so far."""
        return self.n_high - self.n_low

    def cascade_active(self) -> bool:
        """A cascade is active once the public lead is >= 2 (one action leads the
        other by two): then any single private signal is outweighed."""
        return abs(self.d) >= 2

    # -- one agent acts --
    def act_one(self, agent: CascadeAgent) -> str:
        """Have ``agent`` decide from the current public tally, then fold its action
        into the tally. Returns the action taken."""
        act = agent.decide(self.d)
        if act == HIGH:
            self.n_high += 1
        else:
            self.n_low += 1
        return act

    # -- run one queue --
    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Step every agent once, in queue order, and summarise the realised queue.

        Records the first index at which a cascade becomes active (the +-2 barrier is
        first reached), its direction, whether that direction matches the hidden state,
        and the number of agents that acted on private information (revealed their
        signal) before the cascade began.
        """
        cascade_started_at: Optional[int] = None  # 1-based agent index that triggered it
        cascade_dir: Optional[str] = None
        agents_before_cascade = 0

        for agent in self.agent_list:
            was_active = self.cascade_active()
            self.act_one(agent)
            if not was_active:
                # This agent acted on private info (it was not yet a cascade when it
                # decided). If its action pushed the lead to >= 2, the cascade begins
                # with the NEXT agent.
                agents_before_cascade += 1
            if cascade_started_at is None and self.cascade_active():
                cascade_started_at = agent.id + 1  # 1-based index of the trigger action
                cascade_dir = HIGH if self.d > 0 else LOW

        formed = cascade_started_at is not None
        correct = (cascade_dir == self.true_state) if formed else None
        return {
            "n": self.n,
            "p": self.p,
            "seed": self.seed_value,
            "true_state": self.true_state,
            "cascade_formed": formed,
            "cascade_start_index": cascade_started_at,     # 1-based (None if never)
            "cascade_direction": cascade_dir,              # "H"/"L"/None
            "cascade_correct": correct,                    # bool/None
            "agents_before_cascade": agents_before_cascade,  # revealed private info
            "final_d": self.d,
            "n_high": self.n_high,
            "n_low": self.n_low,
        }


# -- closed-form references (the locked grading targets) ----------------------

def prob_no_cascade_after_pairs(p: float, k: int) -> float:
    """P(no cascade after k balanced PAIRS) = (2 p (1-p))^k.

    From a balanced history each fresh pair stays balanced (signals disagree) w.p.
    2p(1-p); k independent pairs all staying balanced gives this."""
    return (2.0 * p * (1.0 - p)) ** k


def prob_incorrect_given_cascade(p: float) -> float:
    """P(cascade is wrong | a cascade formed) = (1-p)^2 / (p^2 + (1-p)^2).

    A cascade is triggered by the first agreeing pair; it points the right way if that
    pair agrees on the correct signal (both correct, w.p. p^2) and the wrong way if it
    agrees on the wrong one (both wrong, w.p. (1-p)^2), conditioned on agreement."""
    q = 1.0 - p
    return (q * q) / (p * p + q * q)


def expected_agents_before_cascade(p: float) -> float:
    """E[agents acting on private info before a cascade] = 2 / (p^2 + (1-p)^2).

    The number of balanced pairs up to and including the triggering pair is geometric
    with success probability r = p^2 + (1-p)^2 per pair; E[pairs] = 1/r, and each pair
    is two agents, so E[agents] = 2/r."""
    q = 1.0 - p
    return 2.0 / (p * p + q * q)


def social_accuracy_gain(p: float) -> float:
    """P(a cascade is correct) - p = p^2/(p^2+(1-p)^2) - p.

    How much a herding late agent beats a lone agent's accuracy p. Small (<=0.16 at
    p=0.7): observing the herd barely improves on one's own signal, because the herd
    only ever aggregates the single triggering pair's information."""
    q = 1.0 - p
    return (p * p) / (p * p + q * q) - p


# -- Monte-Carlo driver -------------------------------------------------------

def run_single(*, n: int = 30, p: float = 0.7, seed: int = 0) -> Dict[str, Any]:
    """Simulate one seeded BHW queue and return its summary."""
    return CascadeModel(n=n, p=p, seed=seed).run()


def run_monte_carlo(*, n: int = 30, p: float = 0.7, n_queues: int = 200_000,
                    seed_base: int = 0) -> Dict[str, Any]:
    """Monte-Carlo over ``n_queues`` independent seeded queues at precision p.

    Each queue uses seed ``seed_base + i`` (a deterministic ensemble). Aggregates the
    locked observables:
      * cascade formation fraction, and formation-by-agent-20 fraction (P1);
      * P(incorrect | cascade) (P2);
      * mean agents acting on private info before a cascade (P3, over queues that
        formed one); and the realised cascade accuracy vs a lone agent's p.

    Returns the empirical estimates plus their closed-form references and binomial
    standard errors, so the caller can grade |empirical - closed form| against a
    tolerance without recomputing anything.
    """
    if n_queues < 1:
        raise ValueError(f"n_queues must be >= 1 (got {n_queues})")

    n_formed = 0
    n_formed_by_20 = 0
    n_incorrect = 0
    n_correct = 0
    sum_before = 0            # agents-before-cascade, over queues that formed one
    n_before_samples = 0
    # keep a small sample of per-queue records for inspection / tests
    sample: List[Dict[str, Any]] = []

    for i in range(n_queues):
        res = run_single(n=n, p=p, seed=seed_base + i)
        if res["cascade_formed"]:
            n_formed += 1
            start = res["cascade_start_index"]
            if start is not None and start <= 20:
                n_formed_by_20 += 1
            if res["cascade_correct"]:
                n_correct += 1
            else:
                n_incorrect += 1
            sum_before += res["agents_before_cascade"]
            n_before_samples += 1
        if i < 5:
            sample.append(res)

    frac_formed = n_formed / n_queues
    frac_formed_by_20 = n_formed_by_20 / n_queues
    p_incorrect = (n_incorrect / n_formed) if n_formed else float("nan")
    p_correct = (n_correct / n_formed) if n_formed else float("nan")
    mean_before = (sum_before / n_before_samples) if n_before_samples else float("nan")

    # closed-form references
    cf_p_incorrect = prob_incorrect_given_cascade(p)
    cf_expected_before = expected_agents_before_cascade(p)
    cf_social_gain = social_accuracy_gain(p)
    # analytic P(no cascade by agent 20) = P(still balanced after 10 pairs)
    cf_no_cascade_by_20 = prob_no_cascade_after_pairs(p, 10)

    def _binom_se(frac: float) -> float:
        return (frac * (1.0 - frac) / n_queues) ** 0.5 if n_queues else float("nan")

    return {
        "n": n,
        "p": p,
        "n_queues": n_queues,
        "seed_base": seed_base,
        # P1 — formation
        "frac_cascade_formed": frac_formed,
        "frac_cascade_formed_by_agent_20": frac_formed_by_20,
        "frac_no_cascade_by_agent_20": 1.0 - frac_formed_by_20,
        "cf_no_cascade_by_agent_20": cf_no_cascade_by_20,
        "se_frac_no_cascade_by_20": _binom_se(1.0 - frac_formed_by_20),
        # P2 — wrong cascades
        "p_incorrect_given_cascade": p_incorrect,
        "cf_p_incorrect_given_cascade": cf_p_incorrect,
        "se_p_incorrect": _binom_se(p_incorrect) if n_formed else float("nan"),
        # P3 — early onset + impaired social learning
        "mean_agents_before_cascade": mean_before,
        "cf_expected_agents_before_cascade": cf_expected_before,
        "p_cascade_correct": p_correct,
        "social_accuracy_gain": (p_correct - p) if n_formed else float("nan"),
        "cf_social_accuracy_gain": cf_social_gain,
        "lone_agent_accuracy": p,
        # raw counts + a small inspection sample
        "n_formed": n_formed,
        "n_formed_by_agent_20": n_formed_by_20,
        "n_correct": n_correct,
        "n_incorrect": n_incorrect,
        "sample_queues": sample,
    }
