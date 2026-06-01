"""Diagnostic: is the Deffuant consensus state absorbing under a falling mu?

Throwaway diagnostic (not part of the demo). Prints real numbers only —
no conclusions written. Answers: does the equilibrate-then-ramp design
fail to reach polarization because (a) the consensus state is genuinely
absorbing under decreasing mu, or (b) the ramp simply did not go low
enough / the perturbation drowned the signal?

Check A: sweep mu_lo from 0.10 down to 0.005. Does a lower floor ever
         trigger a cluster split?
Check B: same sweep with perturb=0 (rule out noise-domination).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from examples.method_transfer_csd_opinion.run_demo import run_one


def summarize(mu_lo: float, perturb: float, seed: int = 0) -> str:
    r = run_one(seed=seed, mu_lo=mu_lo, perturb=perturb)
    b = r["burn_in"]
    v = r["var_series"]
    c = r["clusters"]
    return (
        f"mu_lo={mu_lo:<6} perturb={perturb:<6} "
        f"T*={str(r['transition_tick']):<6} "
        f"final_clusters={c[-1]:<3} max_clusters={max(c):<3} "
        f"var@burn={v[b]:.5f} var@end={v[-1]:.5f}"
    )


print("=== Check A: mu_lo sweep, perturb=0.015 (default) ===")
for mu_lo in [0.10, 0.06, 0.04, 0.02, 0.01, 0.005]:
    print(summarize(mu_lo, perturb=0.015))

print("\n=== Check B: mu_lo sweep, perturb=0 (no noise) ===")
for mu_lo in [0.10, 0.06, 0.04, 0.02, 0.01, 0.005]:
    print(summarize(mu_lo, perturb=0.0))
