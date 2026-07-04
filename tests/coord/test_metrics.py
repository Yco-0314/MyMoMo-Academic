from abm_auto.coord._metrics import makespan, completion_rate, peak_overload

_RES = {
    "t1": {"status": "done", "start_tick": 0, "done_tick": 5},
    "t2": {"status": "done", "start_tick": 2, "done_tick": 9},
    "t3": {"status": "failed", "start_tick": 3, "done_tick": None},
    "_peak_overload": 1.4,
}


def test_makespan_is_latest_done_with_penalty_for_failed():
    # latest done = 9; one failed critical task adds the pre-registered penalty
    assert makespan(_RES, fail_penalty=100.0) == 9 + 100.0


def test_makespan_penalizes_pending_not_just_failed():
    # DAG collapse: one early task failed, the rest stuck 'pending' (upstream failed).
    # The OLD bug counted only 'failed' -> a collapse scored as a fast finish
    # (5 + 1*penalty), inverting node-removal comparisons. The fix penalizes EVERY
    # non-done task (1 failed + 2 pending = 3).
    collapsed = {
        "t1": {"status": "done", "start_tick": 0, "done_tick": 5},
        "t2": {"status": "failed", "start_tick": 5, "done_tick": None},
        "t3": {"status": "pending", "start_tick": None, "done_tick": None},
        "t4": {"status": "pending", "start_tick": None, "done_tick": None},
    }
    healthy = {
        "t1": {"status": "done", "start_tick": 0, "done_tick": 5},
        "t2": {"status": "done", "start_tick": 5, "done_tick": 12},
        "t3": {"status": "done", "start_tick": 8, "done_tick": 18},
        "t4": {"status": "done", "start_tick": 10, "done_tick": 20},
    }
    assert makespan(collapsed, fail_penalty=30.0) == 5 + 30.0 * 3  # 3 non-done
    assert makespan(collapsed, fail_penalty=30.0) > makespan(healthy, fail_penalty=30.0)


def test_completion_rate():
    assert abs(completion_rate(_RES) - 2 / 3) < 1e-9


def test_peak_overload_passthrough():
    assert peak_overload(_RES) == 1.4
