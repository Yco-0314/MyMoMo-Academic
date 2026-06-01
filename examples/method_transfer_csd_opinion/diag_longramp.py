"""Diagnostic: does a LONG ramp give CSD a clean quasi-static approach window?

Writes machine-readable JSON only. No prose, no conclusions.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from abm_auto.analysis.critical_slowing_down import critical_slowing_down
from abm_auto.analysis.method_transfer_guard import test_against_null
from examples.method_transfer_csd_opinion.run_demo import run_one


def inspect(ramp: int, seed: int = 0, mu_lo: float = 0.02, perturb: float = 0.015) -> dict:
    r = run_one(seed=seed, ramp=ramp, mu_lo=mu_lo, perturb=perturb)
    b = r["burn_in"]
    v = r["var_series"]
    T = r["transition_tick"]
    total = len(v)
    end = T if (T is not None and T > b + 20) else total
    pre = v[b:end]
    out = {
        "ramp": ramp, "total": total, "T_star": T,
        "T_frac": round(T / total, 3) if T else None,
        "max_clusters": int(max(r["clusters"])),
        "pre_len": int(len(pre)),
    }
    if len(pre) >= 10:
        idx = np.linspace(0, len(pre) - 1, 5).astype(int)
        out["var_samples"] = [round(float(pre[i]), 6) for i in idx]
        csd = critical_slowing_down(pre)
        stat = lambda s: critical_slowing_down(s).ews_strength
        out["ews"] = round(csd.ews_strength, 3)
        out["var_tau"] = round(csd.variance_tau, 3)
        out["ar1_tau"] = round(csd.ar1_tau, 3)
        out["p_phase"] = round(test_against_null(pre, stat, n_surrogates=200, null_kind="phase", seed=seed).p_value, 4)
        out["p_shuffle"] = round(test_against_null(pre, stat, n_surrogates=200, null_kind="shuffle", seed=seed).p_value, 4)
    return out


results = [inspect(ramp) for ramp in [240, 500, 1000, 2000]]
path = Path(__file__).parent / "diag_longramp_result.json"
path.write_text(json.dumps(results, indent=2))
print(f"wrote {path}")
