"""Method-transfer Demo 1 — Critical Slowing Down × Deffuant opinion dynamics.

Scientific claim (mirrors GeomHerd's structure): an early-warning signal
fires BEFORE the order parameter onset. Here the order parameter is the
opinion-cluster count; the early-warning signal is critical slowing down
(rising AR1 + variance) in the opinion-variance trajectory.

Experiment design
-----------------
Standard Deffuant runs a FIXED confidence threshold μ and just relaxes to
its attractor — no bifurcation crossing, so no genuine CSD test. To make
a real test we RAMP μ downward through the consensus→polarization
bifurcation (μ ≈ 0.27, where surviving clusters ≈ 1/(2μ)):

    μ(t): starts in the consensus regime (high μ, 1 cluster),
          ramps down into the polarization regime (low μ, many clusters).

The cluster count jumps from 1 to several at some tick T*. The CSD claim:
the early-warning signal in opinion_variance rises measurably BEFORE T*.

Dynamics fidelity
-----------------
The pairwise Deffuant update here is identical to
``examples/calibration_challenge_opinion/handcrafted_model/core/environment.py``
(symmetric: both agents move toward each other by α if |Δ| < μ), on a
real Watts-Strogatz small-world network. The only addition is the μ ramp,
which the calibration example holds fixed.

Anti-spurious guard
-------------------
The CSD signal is tested against shuffle + phase surrogate nulls
(method_transfer_guard). A signal that doesn't beat its null is reported
as "no signal above null" — non-findings are reported, not hidden.

Usage:
    python examples/method_transfer_csd_opinion/run_demo.py [n_seeds=8]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO))

from abm_auto.analysis.critical_slowing_down import critical_slowing_down
from abm_auto.analysis.method_transfer_guard import test_against_null


def _watts_strogatz(n: int, k: int, p: float, rng: np.random.Generator) -> list[list[int]]:
    """Adjacency list for a Watts-Strogatz small-world graph (same topology
    family the opinion example uses)."""
    adj: list[set[int]] = [set() for _ in range(n)]
    half = k // 2
    for i in range(n):
        for j in range(1, half + 1):
            a, b = i, (i + j) % n
            adj[a].add(b)
            adj[b].add(a)
    # Rewire
    for i in range(n):
        for j in range(1, half + 1):
            if rng.random() < p:
                cur = (i + j) % n
                choices = [x for x in range(n) if x != i and x not in adj[i]]
                if choices:
                    new = int(rng.choice(choices))
                    adj[i].discard(cur)
                    adj[cur].discard(i)
                    adj[i].add(new)
                    adj[new].add(i)
    return [sorted(s) for s in adj]


def _opinion_clusters(ops: np.ndarray, gap: float = 0.10) -> int:
    """Same gap-counting cluster metric as the opinion example."""
    s = np.sort(ops)
    return 1 + int(np.sum(np.diff(s) > gap))


def run_one(seed: int, n_agents: int = 200,
            burn_in: int = 60, ramp: int = 240,
            k: int = 8, mu_hi: float = 0.45, mu_lo: float = 0.06,
            alpha: float = 0.30, perturb: float = 0.015) -> dict:
    """One equilibrate-then-ramp Deffuant run.

    Proper CSD test requires the system to track a slowly-moving control
    parameter from a quasi-equilibrium, not to start far from attractor.
    So:

      Phase A (burn-in, fixed high μ): from uniform-random, let Deffuant
        relax to CONSENSUS (1 cluster, low variance). The system is now
        on a stable branch.

      Phase B (slow ramp): lower μ linearly from mu_hi to mu_lo over
        `ramp` ticks. Consensus loses stability as μ → μ_c; recovery from
        the matching-noise perturbations slows (critical slowing down)
        BEFORE the consensus branch splits into polarized clusters.

    A small per-tick perturbation (`perturb`) injects the noise CSD needs
    to measure recovery rate — analogous to demographic/environmental
    noise in ecological EWS. Without a noise source a deterministic
    consensus has no fluctuations to slow down.
    """
    rng = np.random.default_rng(seed)
    adj = _watts_strogatz(n_agents, k, 0.10, rng)
    ops = rng.random(n_agents)

    periods = burn_in + ramp
    mu_schedule = np.concatenate([
        np.full(burn_in, mu_hi),
        np.linspace(mu_hi, mu_lo, ramp),
    ])
    var_series = np.zeros(periods)
    clusters = np.zeros(periods, dtype=int)

    def _step(mu: float) -> None:
        for a in range(n_agents):
            nbrs = adj[a]
            if not nbrs:
                continue
            b = int(rng.choice(nbrs))
            diff = ops[b] - ops[a]
            if abs(diff) < mu:
                ops[a] += alpha * diff
                ops[b] -= alpha * diff

    for t in range(periods):
        mu = float(mu_schedule[t])
        var_series[t] = float(np.var(ops))
        clusters[t] = _opinion_clusters(ops)
        _step(mu)
        # small bounded perturbation = the noise source CSD measures
        ops += rng.normal(0.0, perturb, n_agents)
        np.clip(ops, 0.0, 1.0, out=ops)

    # Transition tick T*: first ramp-phase tick where clusters hits >= 2
    transition = None
    for t in range(burn_in, periods):
        if clusters[t] >= 2:
            transition = t
            break

    return {
        "seed": seed,
        "burn_in": burn_in,
        "var_series": var_series,
        "clusters": clusters,
        "transition_tick": transition,
        "mu_schedule": mu_schedule,
    }


def analyze_run(run: dict) -> dict:
    """CSD on the PRE-transition window + null test. The science: does the
    early-warning signal rise before the cluster split?"""
    # Pre-transition window: from end of burn-in up to the split. This is
    # the slow-approach regime where CSD theory predicts a rising signal.
    var = run["var_series"]
    T = run["transition_tick"]
    burn = run["burn_in"]
    end = T if (T is not None and T > burn + 20) else len(var)
    pre = var[burn:end]

    csd = critical_slowing_down(pre)
    stat = lambda s: critical_slowing_down(s).ews_strength
    guard_shuffle = test_against_null(pre, stat, n_surrogates=200, null_kind="shuffle", seed=run["seed"])
    guard_phase = test_against_null(pre, stat, n_surrogates=200, null_kind="phase", seed=run["seed"])

    return {
        "seed": run["seed"],
        "transition_tick": T,
        "pre_window_len": int(end),
        "ews_strength": csd.ews_strength,
        "ar1_tau": csd.ar1_tau,
        "variance_tau": csd.variance_tau,
        "p_shuffle": guard_shuffle.p_value,
        "p_phase": guard_phase.p_value,
        "z_shuffle": guard_shuffle.z_score,
        "significant": guard_shuffle.significant and guard_phase.significant,
    }


def main() -> int:
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    print(f"=== Method-transfer Demo 1: CSD × Deffuant (ramped μ), {n_seeds} seeds ===\n")

    results = []
    for seed in range(n_seeds):
        run = run_one(seed)
        res = analyze_run(run)
        results.append(res)
        T = res["transition_tick"]
        print(
            f"seed {seed}: T*={T} ews={res['ews_strength']:+.3f} "
            f"(ar1τ={res['ar1_tau']:+.2f} varτ={res['variance_tau']:+.2f}) "
            f"p_shuf={res['p_shuffle']:.3f} p_phase={res['p_phase']:.3f} "
            f"{'SIGNIFICANT' if res['significant'] else 'no signal'}"
        )

    # Holdout aggregate: how many seeds beat BOTH nulls (strict).
    # NOTE: this demo is a documented NEGATIVE — see FINDINGS.md. CSD does
    # not transfer to Deffuant (structural mismatch). The aggregate below
    # is descriptive, not a pass/fail gate; do not read a high count as
    # "validated" without the per-config null detail in FINDINGS.md.
    n_sig = sum(r["significant"] for r in results)
    mean_ews = float(np.mean([r["ews_strength"] for r in results]))
    print(f"\n--- Holdout aggregate ({n_seeds} seeds) ---")
    print(f"Seeds beating both nulls (p<0.05): {n_sig}/{n_seeds}")
    print(f"Mean EWS strength: {mean_ews:+.3f}")
    print("See FINDINGS.md — verdict is NEGATIVE (structural mismatch).")

    out = REPO / "examples" / "method_transfer_csd_opinion" / "demo_result.json"
    out.write_text(json.dumps(
        [{k: (v if not isinstance(v, np.ndarray) else None) for k, v in r.items()} for r in results],
        indent=2, default=float,
    ))
    print(f"\nResult: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
