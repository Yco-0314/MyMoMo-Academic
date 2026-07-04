"""Outcome metrics for a CoordModel run dict. makespan is the PRIMARY outcome."""
from __future__ import annotations


def _tasks(res: dict):
    return {k: v for k, v in res.items() if not k.startswith("_")}


#: Default per-failed-task penalty (v2). Chosen so makespan is TIMING-driven:
#: with functional baselines a full run completes in roughly 15-30 ticks, so a
#: penalty of ~30 makes a single genuine failure strictly worse than any
#: all-complete finish, yet keeps makespan on the same scale as response timing
#: (a failure costs "about one extra run's worth" of delay) rather than swamping
#: it 100x as in v1. Not tuned to any cross-treatment outcome.
DEFAULT_FAIL_PENALTY = 30.0


def makespan(res: dict, *, fail_penalty: float = DEFAULT_FAIL_PENALTY) -> float:
    """Latest completion tick + a pre-registered penalty per NON-DONE task. Lower
    is better. Penalty makes "didn't finish" strictly worse than any finish.

    A task is non-done if its status is anything but ``done`` — `failed` OR
    `pending`/`active` (e.g. a task whose upstream failed never becomes eligible
    and stays `pending`). Counting only `failed` was a bug: a TOTAL DAG collapse
    (one early failure stalling everything downstream as `pending`) scored as a
    fast finish (latest done_tick of the few completed tasks + 1*penalty), which
    inverted node-removal comparisons. Penalising every non-done task fixes this."""
    t = _tasks(res)
    done = [v["done_tick"] for v in t.values() if v["status"] == "done" and v["done_tick"] is not None]
    n_nondone = sum(1 for v in t.values() if v["status"] != "done")
    base = max(done) if done else 0.0
    return float(base + fail_penalty * n_nondone)


def completion_rate(res: dict) -> float:
    t = _tasks(res)
    if not t:
        return 0.0
    return sum(1 for v in t.values() if v["status"] == "done") / len(t)


def peak_overload(res: dict) -> float:
    return float(res.get("_peak_overload", 0.0))
