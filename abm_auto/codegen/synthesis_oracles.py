"""Real oracle paradigms for the Synthesis Phase (ADR-015).

Each oracle is an INDEPENDENT known-answer test: it takes a candidate operator
(the thing the synthesis step drafts) and returns True iff the candidate
reproduces a KNOWN answer on a fixed problem. The answer is independent of the
candidate's implementation — that independence is what makes the oracle a real
judge and not self-certification (ADR-013).

Each paradigm documents a CANDIDATE PROTOCOL (the small interface the candidate
must satisfy); the LLM synthesis step drafts to it, the oracle exercises it.
Library-grade: deterministic, self-tested below with a reference-correct and a
reference-buggy candidate, so a synthesized operator that PASSES one of these is
genuinely verified.
"""
from __future__ import annotations

import itertools
import random


# ── tabular Q-learning ───────────────────────────────────────────────────────
# Candidate protocol: make(n_states, n_actions) -> object with
#   .update(s, a, r, s2)   (one TD step)
#   .best_action(s) -> int
# Known problem: a 3-state chain (0,1,2; goal=2). Right (a=1) advances and
# yields reward 1 on reaching 2; left (a=0) retreats. Optimal policy: always go
# right. The oracle trains the candidate, then checks it recovers that policy.

def _chain_step(s: int, a: int):
    s2 = min(2, s + 1) if a == 1 else max(0, s - 1)
    return s2, (1.0 if s2 == 2 else 0.0)


def oracle_tabular_q(make) -> bool:
    try:
        rng = random.Random(0)
        q = make(3, 2)
        for _ in range(400):
            s = 0
            for _ in range(12):
                a = rng.randint(0, 1) if rng.random() < 0.3 else q.best_action(s)
                s2, r = _chain_step(s, a)
                q.update(s, a, r, s2)
                s = s2
                if s == 2:
                    break
        return q.best_action(0) == 1 and q.best_action(1) == 1
    except Exception:
        return False


class _RefQ:
    def __init__(self, ns, na, lr=0.5, gamma=0.9):
        self.Q = [[0.0] * na for _ in range(ns)]
        self.lr, self.g = lr, gamma

    def update(self, s, a, r, s2):
        self.Q[s][a] += self.lr * (r + self.g * max(self.Q[s2]) - self.Q[s][a])

    def best_action(self, s):
        return max(range(len(self.Q[s])), key=lambda a: self.Q[s][a])


class _BuggyQ:                       # never learns → policy stuck at action 0
    def __init__(self, ns, na): ...
    def update(self, *a): ...
    def best_action(self, s): return 0


# ── Kalman filter (1-D constant) ─────────────────────────────────────────────
# Candidate protocol: make() -> object with .update(obs) and .estimate() -> float
# Known problem: noisy observations of a constant (true = 5.0). The estimate
# must converge near the truth.

def oracle_kalman(make) -> bool:
    try:
        rng = random.Random(0)
        kf = make()
        true = 5.0
        for _ in range(300):
            kf.update(true + rng.gauss(0.0, 1.0))
        return abs(kf.estimate() - true) < 0.4
    except Exception:
        return False


class _RefKalman:
    def __init__(self):
        self.x, self.P, self.R = 0.0, 1.0, 1.0

    def update(self, obs):
        K = self.P / (self.P + self.R)
        self.x += K * (obs - self.x)
        self.P = self.P * (1 - K) + 1e-3      # tiny process noise → keeps tracking

    def estimate(self):
        return self.x


class _BuggyKalman:                  # ignores observations
    def update(self, obs): ...
    def estimate(self): return 0.0


# ── linear program (2-var) ───────────────────────────────────────────────────
# Candidate protocol: make() -> solve(c, A_ub, b_ub) -> x minimizing c·x s.t.
#   A_ub·x <= b_ub, x >= 0.
# Known problem: min -x0-x1 s.t. x0+2x1<=4, 3x0+x1<=6 → optimum (1.6,1.2),
# objective -2.8.

_LP_C = [-1.0, -1.0]
_LP_A = [[1.0, 2.0], [3.0, 1.0]]
_LP_B = [4.0, 6.0]
_LP_OPT = -2.8


def oracle_linear_program(make) -> bool:
    try:
        solve = make()
        x = solve(list(_LP_C), [row[:] for row in _LP_A], list(_LP_B))
        feasible = (
            all(sum(_LP_A[i][j] * x[j] for j in range(2)) <= _LP_B[i] + 1e-6
                for i in range(2))
            and all(xi >= -1e-6 for xi in x)
        )
        obj = sum(_LP_C[j] * x[j] for j in range(2))
        return feasible and abs(obj - _LP_OPT) < 0.05
    except Exception:
        return False


def _ref_lp():
    def solve(c, A, b):
        n = len(c)
        cons = [(A[i][:], b[i]) for i in range(len(A))]
        for j in range(n):                       # x_j >= 0  ->  -x_j <= 0
            row = [0.0] * n; row[j] = -1.0
            cons.append((row, 0.0))
        best, best_obj = None, None
        for (r1, b1), (r2, b2) in itertools.combinations(cons, 2):
            det = r1[0] * r2[1] - r1[1] * r2[0]
            if abs(det) < 1e-9:
                continue
            x = [(b1 * r2[1] - b2 * r1[1]) / det, (r1[0] * b2 - r2[0] * b1) / det]
            if all(sum(A[i][j] * x[j] for j in range(n)) <= b[i] + 1e-6
                   for i in range(len(A))) and all(xi >= -1e-6 for xi in x):
                o = sum(c[j] * x[j] for j in range(n))
                if best_obj is None or o < best_obj:
                    best, best_obj = x, o
        return best or [0.0] * n
    return solve


def _buggy_lp():
    def solve(c, A, b):
        return [0.0] * len(c)                     # feasible but not optimal
    return solve


# ── the library (paradigm name -> oracle) + self-test ────────────────────────

REAL_ORACLES = {
    "tabular_q_learning": oracle_tabular_q,
    "kalman_filter": oracle_kalman,
    "linear_program": oracle_linear_program,
}


def self_test() -> bool:
    """Each oracle PASSES its reference-correct candidate and REJECTS the buggy
    one — proving the oracle genuinely discriminates (a synthesized operator
    that passes it is verified, not laundered)."""
    cases = [
        (oracle_tabular_q, (lambda ns, na: _RefQ(ns, na)), _BuggyQ),
        (oracle_kalman, _RefKalman, _BuggyKalman),
        (oracle_linear_program, _ref_lp, _buggy_lp),
    ]
    for oracle, good, bad in cases:
        if not oracle(good):
            return False
        if oracle(bad):
            return False
    return True
