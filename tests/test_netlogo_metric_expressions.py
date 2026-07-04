from __future__ import annotations

import math

import pytest

import abm_auto.netlogo_metrics as netlogo_metrics
from abm_auto.netlogo_metrics import (
    evaluate_netlogo_metric,
    netlogo_metric_expression_gate,
)
from abm_auto.netlogo_semantics import NetLogoWorld


def _sir_world() -> NetLogoWorld:
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_turtles(3, **{"infected?": False, "resistant?": False})
    world.create_turtles(2, **{"infected?": True, "resistant?": False})
    world.create_turtles(1, **{"infected?": False, "resistant?": True})
    return world


def _link_world() -> tuple[NetLogoWorld, list]:
    world = NetLogoWorld(seed=0, schedule="sequential")
    turtles = world.create_turtles(4).snapshot()
    world.create_patches(0, 1, 0, 1, color="green")
    world.create_link(turtles[0], turtles[1])
    world.create_link(turtles[0], turtles[2])
    world.create_link(turtles[0], turtles[3], directed=True)
    return world, turtles


def _link_predicate_world() -> tuple[NetLogoWorld, list]:
    world, turtles = _link_world()
    turtles[1].set("infected?", True).set("resistant?", False)
    turtles[2].set("infected?", False).set("resistant?", False)
    turtles[3].set("infected?", True).set("resistant?", True)
    return world, turtles


def test_evaluates_virus_count_metrics():
    world = _sir_world()

    assert evaluate_netlogo_metric(world, "count turtles") == 6
    assert evaluate_netlogo_metric(world, "count turtles with [infected?]") == 2
    assert evaluate_netlogo_metric(world, "count turtles with [resistant?]") == 1
    assert (
        evaluate_netlogo_metric(
            world,
            "count turtles with [not infected? and not resistant?]",
        )
        == 3
    )


def test_evaluates_virus_plot_percentage_expressions():
    world = _sir_world()

    assert (
        evaluate_netlogo_metric(
            world,
            (
                "plot (count turtles with [not infected? and not resistant?]) "
                "/ (count turtles) * 100"
            ),
        )
        == 50.0
    )
    assert math.isclose(
        evaluate_netlogo_metric(
            world,
            "plot (count turtles with [infected?]) / (count turtles) * 100",
        ),
        100.0 / 3.0,
    )
    assert math.isclose(
        evaluate_netlogo_metric(
            world,
            "plot (count turtles with [resistant?]) / (count turtles) * 100",
        ),
        100.0 / 6.0,
    )


def test_evaluates_link_count_metrics():
    world, turtles = _link_world()

    assert evaluate_netlogo_metric(world, "count links") == 3
    assert evaluate_netlogo_metric(world, "(count links) + 2") == 5
    assert evaluate_netlogo_metric(world, "count link-neighbors", context=turtles[0]) == 2
    assert evaluate_netlogo_metric(world, "count link-neighbors", context=turtles[3]) == 0
    assert (
        evaluate_netlogo_metric(
            world,
            "(count links) + (count link-neighbors)",
            context=turtles[0],
        )
        == 5
    )


def test_rejects_link_neighbors_without_valid_context():
    world, turtles = _link_world()
    other_world = NetLogoWorld(seed=0, schedule="sequential")
    other_turtle = other_world.create_turtles(1).snapshot()[0]

    for context in (None, object(), other_turtle):
        with pytest.raises(ValueError, match="Unsupported NetLogo metric expression"):
            evaluate_netlogo_metric(world, "count link-neighbors", context=context)

    assert evaluate_netlogo_metric(world, "count link-neighbors", context=turtles[1]) == 1


def test_evaluates_filtered_link_neighbor_count_metrics():
    world, turtles = _link_predicate_world()

    assert (
        evaluate_netlogo_metric(
            world,
            "count link-neighbors with [infected?]",
            context=turtles[0],
        )
        == 1
    )
    assert (
        evaluate_netlogo_metric(
            world,
            "count link-neighbors with [not infected?]",
            context=turtles[0],
        )
        == 1
    )
    assert (
        evaluate_netlogo_metric(
            world,
            "count link-neighbors with [not infected? and not resistant?]",
            context=turtles[0],
        )
        == 1
    )
    assert (
        evaluate_netlogo_metric(
            world,
            "(count link-neighbors with [infected?]) * 10",
            context=turtles[0],
        )
        == 10
    )
    assert (
        evaluate_netlogo_metric(
            world,
            "count link-neighbors with [infected?]",
            context=turtles[3],
        )
        == 0
    )


def test_rejects_filtered_link_neighbors_without_valid_context():
    world, _ = _link_predicate_world()
    other_world = NetLogoWorld(seed=0, schedule="sequential")
    other_turtle = other_world.create_turtles(1).snapshot()[0]

    for context in (None, object(), other_turtle):
        with pytest.raises(ValueError, match="Unsupported NetLogo metric expression"):
            evaluate_netlogo_metric(
                world,
                "count link-neighbors with [infected?]",
                context=context,
            )


@pytest.mark.parametrize(
    "expression",
    [
        "count turtles with [infected? or resistant?]",
        "sum [energy] of turtles",
        "__import__('os').system('echo unsafe')",
    ],
)
def test_rejects_unsupported_metric_expressions(expression):
    with pytest.raises(ValueError, match="Unsupported NetLogo metric expression"):
        evaluate_netlogo_metric(_sir_world(), expression)


def test_netlogo_metric_expression_gate_passes_with_limited_boundary():
    ok, message = netlogo_metric_expression_gate()

    assert ok is True
    assert "limited metric expression family" in message
    assert "not general NetLogo execution" in message


def test_netlogo_link_metric_gate_passes_with_limited_boundary():
    ok, message = netlogo_metrics.netlogo_link_metric_gate()

    assert ok is True
    assert "limited link metric family" in message
    assert "not general NetLogo execution" in message


def test_netlogo_link_predicate_gate_passes_with_limited_boundary():
    ok, message = netlogo_metrics.netlogo_link_predicate_gate()

    assert ok is True
    assert "limited link predicate family" in message
    assert "not general NetLogo execution" in message
