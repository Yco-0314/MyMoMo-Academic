"""Faithful-rule + determinism tests for the Nagel-Schreckenberg traffic
(Nagel & Schreckenberg 1992) reproduction.

These pin the defining rules — the four parallel update steps (accelerate, brake
to the gap, randomize, move), the ring (periodic) gap-to-next-car geometry, the
no-overlap invariant, velocity bounds [0, vmax], the p=0 deterministic free-flow
limit, and flow = rho * <v> — plus determinism (same seed -> identical run). They
are faithfulness tests, NOT prediction tests (P1-P3 are evaluated by
examples/repro_nagel_schreckenberg/run.py).
"""
from __future__ import annotations

from abm_auto.classics.nagel_schreckenberg import (
    CarAgent,
    NagelSchreckenbergModel,
    argmax_flow_density,
    mean,
    run_single,
    std,
    sweep_density,
    variance,
)


# -- construction / placement -------------------------------------------------

def test_from_density_places_round_rho_times_length_cars():
    m = NagelSchreckenbergModel.from_density(0.1, length=1000)
    assert m.n_cars == 100
    assert len(m.cars) == 100
    # density property reflects the actual car count.
    assert abs(m.density - 0.1) < 1e-12


def test_cars_placed_on_distinct_cells_and_sorted():
    m = NagelSchreckenbergModel(length=50, n_cars=20, seed=4)
    xs = [c.x for c in m.cars]
    assert len(set(xs)) == 20                 # distinct cells
    assert xs == sorted(xs)                    # kept sorted by position
    assert all(0 <= x < 50 for x in xs)


def test_rejects_more_cars_than_cells():
    raised = False
    try:
        NagelSchreckenbergModel(length=10, n_cars=11)
    except ValueError:
        raised = True
    assert raised


def test_rejects_bad_probability():
    for bad in (-0.1, 1.5):
        raised = False
        try:
            NagelSchreckenbergModel(length=100, n_cars=10, p=bad)
        except ValueError:
            raised = True
        assert raised, f"p={bad} should be rejected"


# -- ring geometry: gap to the next car ---------------------------------------

def test_gap_ahead_counts_empty_cells_to_next_car():
    # cars at 0 and 4 on a ring of length 10: gap from car0 to car1 = 3 empty
    # cells (1,2,3); gap from car1 wraps around (5,6,7,8,9,0?) -> cells 5..9 = 5.
    m = NagelSchreckenbergModel(length=10, n_cars=2, seed=0)
    m.cars[0].x, m.cars[1].x = 0, 4
    assert m.gap_ahead(0) == 3                  # cells 1,2,3 between 0 and 4
    assert m.gap_ahead(1) == 5                  # cells 5,6,7,8,9 wrapping to 0


def test_gap_for_lone_car_is_whole_ring_minus_one():
    m = NagelSchreckenbergModel(length=20, n_cars=1, seed=0)
    assert m.gap_ahead(0) == 19                 # never blocks itself


def test_adjacent_cars_have_zero_gap():
    m = NagelSchreckenbergModel(length=10, n_cars=2, seed=0)
    m.cars[0].x, m.cars[1].x = 3, 4
    assert m.gap_ahead(0) == 0                  # no empty cell between them


# -- the four update steps (parallel) -----------------------------------------

def test_brake_step_prevents_overlap():
    # Two cars adjacent (gap 0): after a tick neither moves into the other.
    m = NagelSchreckenbergModel(length=10, n_cars=2, seed=0, p=0.0)
    m.cars[0].x, m.cars[0].v = 0, 5
    m.cars[1].x, m.cars[1].v = 1, 0
    m.step()
    xs = sorted(c.x for c in m.cars)
    assert len(set(xs)) == 2                    # still distinct
    # car behind had gap 0 -> brakes to v=0 -> stays at 0.
    assert 0 in xs


def test_accelerate_caps_at_vmax():
    # A lone car with empty road accelerates by 1 each tick up to vmax, p=0.
    m = NagelSchreckenbergModel(length=1000, n_cars=1, seed=0, p=0.0, vmax=5)
    car = m.cars[0]
    car.x, car.v = 0, 0
    seen = []
    for _ in range(8):
        m.step()
        seen.append(car.v)
    assert seen == [1, 2, 3, 4, 5, 5, 5, 5]     # +1/tick then capped at vmax


def test_randomize_never_applied_when_p_is_zero():
    # With p=0 a free car reaches and holds exactly vmax (deterministic).
    m = NagelSchreckenbergModel(length=1000, n_cars=1, seed=123, p=0.0, vmax=5)
    for _ in range(50):
        m.step()
    assert m.cars[0].v == 5


def test_randomize_with_p_one_always_slows_a_moving_car():
    # With p=1 every moving car loses 1 each tick (after accel+brake).
    m = NagelSchreckenbergModel(length=1000, n_cars=1, seed=0, p=1.0, vmax=5)
    car = m.cars[0]
    car.x, car.v = 0, 0
    vs = []
    for _ in range(6):
        m.step()
        vs.append(car.v)
    # accelerate to 1 then randomize -1 -> 0 every tick: velocity never exceeds 0.
    assert all(v == 0 for v in vs)


def test_velocity_stays_within_bounds_and_no_overlap_over_many_ticks():
    m = NagelSchreckenbergModel(length=200, n_cars=60, seed=9)
    for _ in range(500):
        m.step()
        xs = [c.x for c in m.cars]
        assert len(set(xs)) == len(xs)         # never two cars in one cell
        assert all(0 <= c.v <= m.vmax for c in m.cars)
        assert all(0 <= c.x < m.length for c in m.cars)


def test_update_is_parallel_move_uses_new_velocity():
    # A single car at v computed this tick moves by exactly that v (mod L).
    m = NagelSchreckenbergModel(length=1000, n_cars=1, seed=0, p=0.0)
    car = m.cars[0]
    car.x, car.v = 10, 3
    m.step()
    # accel -> v=4, no brake (lone car), no randomize (p=0) -> moves +4.
    assert car.v == 4
    assert car.x == 14


# -- metrics ------------------------------------------------------------------

def test_mean_velocity_and_stopped_fraction():
    m = NagelSchreckenbergModel(length=100, n_cars=4, seed=0)
    m.cars[0].v, m.cars[1].v, m.cars[2].v, m.cars[3].v = 0, 0, 4, 4
    assert m.mean_velocity() == 2.0            # (0+0+4+4)/4
    assert m.stopped_fraction() == 0.5         # 2 of 4 stopped


def test_flow_is_density_times_mean_velocity():
    r = run_single(0.2, seed=0, transient=100, measure=100)
    assert abs(r["flow"] - r["rho"] * r["mean_velocity"]) < 1e-12
    assert abs(r["rho"] - 0.2) < 1e-12


def test_empty_road_metrics_are_zero():
    m = NagelSchreckenbergModel(length=100, n_cars=0, seed=0)
    assert m.mean_velocity() == 0.0
    assert m.stopped_fraction() == 0.0


def test_mean_variance_std_helpers():
    xs = [2, 4, 6]
    assert mean(xs) == 4.0
    assert abs(variance(xs) - 8 / 3) < 1e-12   # ((-2)^2+0+2^2)/3
    assert abs(std(xs) - (8 / 3) ** 0.5) < 1e-12
    assert mean([]) == 0.0
    assert variance([]) == 0.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_run():
    a = run_single(0.2, seed=42, transient=100, measure=100)
    b = run_single(0.2, seed=42, transient=100, measure=100)
    assert a["flow"] == b["flow"]
    assert a["mean_velocity"] == b["mean_velocity"]
    assert a["stopped_fraction"] == b["stopped_fraction"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(0.3, seed=1, transient=100, measure=100)
    b = run_single(0.3, seed=2, transient=100, measure=100)
    for res in (a, b):
        assert 0.0 <= res["mean_velocity"] <= 5.0
        assert 0.0 <= res["stopped_fraction"] <= 1.0
        assert res["flow"] >= 0.0


# -- fundamental-diagram shape (small, fast anchor) ---------------------------

def test_fundamental_diagram_has_interior_flow_maximum():
    # A short, cheap sweep: the flow argmax is at an interior density, not an
    # endpoint (the qualitative NaSch signature). Full P1-P3 grading lives in the
    # runner; this is a fast structural anchor.
    rhos = [0.05, 0.1, 0.2, 0.5]
    rows = sweep_density(rhos, n_seeds=3, transient=200, measure=200)
    peak = argmax_flow_density(rows)
    assert peak not in (rhos[0], rhos[-1])     # interior, not an endpoint
    # free-flow at low density, jammed at high density.
    low = next(r for r in rows if r["rho"] == 0.05)
    high = next(r for r in rows if r["rho"] == 0.5)
    assert low["mean_velocity"] >= 3.0
    assert high["mean_velocity"] <= 2.0
    assert high["mean_stopped_fraction"] >= 0.1
