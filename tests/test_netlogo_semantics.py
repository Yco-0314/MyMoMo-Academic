"""Executable NetLogo semantic cells on the neutral ABM platform.

These tests do not claim full NetLogo compatibility. They pin the first native
cell: agentsets, breed filtering, ask-over-snapshot, explicit ticks, globals,
and monitor collection.
"""
from __future__ import annotations

import pytest

import abm_auto.netlogo_semantics as netlogo_semantics
from abm_auto.netlogo_semantics import NetLogoWorld


def test_ask_runs_over_snapshot_agentset_and_tick_is_explicit():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_turtles(3, breed="people", asked=0)

    asked_ids = []

    def mark_and_spawn(turtle):
        asked_ids.append(turtle.id)
        turtle["asked"] += 1
        if turtle.id == 0:
            world.create_turtles(1, breed="people", asked=0)

    world.ask(world.turtles, mark_and_spawn)

    assert asked_ids == [0, 1, 2]
    assert len(world.turtles) == 4
    assert [t["asked"] for t in world.turtles.ordered()] == [1, 1, 1, 0]
    assert world.t == 0

    world.tick()
    assert world.t == 1

    world.reset_ticks()
    assert world.t == 0


def test_breed_filtered_agentsets_globals_and_monitors_form_a_minimal_cell():
    world = NetLogoWorld(seed=0, schedule="sequential", globals={"cost": 2})
    world.create_turtles(2, breed="sheep", energy=3)
    world.create_turtles(1, breed="sheep", energy=1)
    world.create_turtles(1, breed="wolf", energy=10)

    world.monitor(
        "energetic_sheep",
        lambda m: len(m.turtles.with_breed("sheep").where(lambda t: t["energy"] > 0)),
    )

    world.collect_monitors()
    world.ask(
        world.turtles.with_breed("sheep"),
        lambda turtle: turtle.set("energy", turtle["energy"] - world.globals["cost"]),
    )
    world.tick()
    world.collect_monitors()

    assert [t["energy"] for t in world.turtles.with_breed("sheep").ordered()] == [1, 1, -1]
    assert [t["energy"] for t in world.turtles.with_breed("wolf").ordered()] == [10]
    assert world.monitor_records == [
        {"t": 0, "energetic_sheep": 3},
        {"t": 1, "energetic_sheep": 2},
    ]


def test_random_order_ask_is_seeded_and_uses_the_world_schedule():
    def ask_order(seed):
        world = NetLogoWorld(seed=seed, schedule="random_order")
        world.create_turtles(8, breed="people")
        order = []
        world.ask(world.turtles, lambda turtle: order.append(turtle.id))
        return order

    first = ask_order(42)
    second = ask_order(42)

    assert first == second
    assert sorted(first) == list(range(8))
    assert first != list(range(8))


def test_one_of_and_n_of_are_seeded_snapshot_selection_helpers():
    def selections(seed):
        world = NetLogoWorld(seed=seed, schedule="sequential")
        turtles = world.create_turtles(6, breed="people")
        one = world.one_of(turtles)
        many = world.n_of(3, turtles)
        return one.id, [t.id for t in many.ordered()]

    assert selections(17) == selections(17)
    one_id, many_ids = selections(17)
    assert one_id in range(6)
    assert len(many_ids) == 3
    assert len(set(many_ids)) == 3


def test_random_selection_validation_fails_clearly():
    world = NetLogoWorld(seed=0, schedule="sequential")
    turtles = world.create_turtles(2, breed="people")

    with pytest.raises(ValueError, match="one_of expects a non-empty collection"):
        world.one_of([])
    with pytest.raises(ValueError, match="n must be a non-negative integer"):
        world.n_of(True, turtles)
    with pytest.raises(ValueError, match="n must be a non-negative integer"):
        world.n_of(-1, turtles)
    with pytest.raises(ValueError, match="n cannot exceed collection size"):
        world.n_of(3, turtles)

    empty = world.n_of(0, turtles)
    assert isinstance(empty, netlogo_semantics.NetLogoAgentSet)
    assert len(empty) == 0


def test_create_link_with_nearest_unlinked_matches_virus_setup_slice():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-2, 2, -1, 2)
    a, b, c, d = world.create_turtles(4, breed="people").ordered()
    a.setxy(0, 0)
    b.setxy(1, 0)
    c.setxy(0, 2)
    d.setxy(-1, 0)

    first = world.create_link_with_nearest_unlinked(a)
    second = world.create_link_with_nearest_unlinked(a)
    third = world.create_link_with_nearest_unlinked(a)
    exhausted = world.create_link_with_nearest_unlinked(a)

    assert (first.end1, first.end2) == (a, b)
    assert (second.end1, second.end2) == (a, d)
    assert (third.end1, third.end2) == (a, c)
    assert exhausted is None
    assert len(world.links) == 3


def test_create_link_with_nearest_unlinked_validates_world_and_candidates():
    world = NetLogoWorld(seed=0, schedule="sequential")
    other = NetLogoWorld(seed=0, schedule="sequential")
    a, b = world.create_turtles(2, breed="people").ordered()
    outsider = other.create_turtles(1, breed="people").ordered()[0]

    with pytest.raises(ValueError, match="source must be a NetLogoTurtle"):
        world.create_link_with_nearest_unlinked(object())
    with pytest.raises(ValueError, match="same NetLogoWorld"):
        world.create_link_with_nearest_unlinked(outsider)
    with pytest.raises(ValueError, match="candidate must be a NetLogoTurtle"):
        world.create_link_with_nearest_unlinked(a, candidates=[b, object()])


def test_netlogo_virus_network_setup_slice_gate_passes_with_boundary_message():
    ok, message = netlogo_semantics.netlogo_virus_network_setup_slice_gate()

    assert ok is True
    assert "Virus setup slice" in message
    assert "not NetLogo procedure execution" in message


def test_patch_grid_creation_and_lookup_are_coordinate_stable():
    world = NetLogoWorld(seed=0, schedule="sequential")
    patches = world.create_patches(-1, 1, -1, 0, heat=0)

    assert len(patches) == 6
    assert [(p.pxcor, p.pycor) for p in patches.ordered()] == [
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (0, 0),
        (1, 0),
    ]
    center = world.patch_at(0, 0)
    assert isinstance(center, netlogo_semantics.NetLogoPatch)
    assert world.patch_at(0, 0) is center
    center["heat"] = 3
    assert center.get("heat") == 3


def test_patch_lookup_and_grid_validation_fail_clearly():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 1)

    with pytest.raises(ValueError, match="patch coordinate"):
        world.patch_at(True, 0)
    with pytest.raises(ValueError, match="patch not found"):
        world.patch_at(2, 2)
    with pytest.raises(ValueError, match="patch grid already exists"):
        world.create_patches(0, 0, 0, 0)

    other = NetLogoWorld(seed=0, schedule="sequential")
    with pytest.raises(ValueError, match="min_pxcor"):
        other.create_patches(True, 1, 0, 1)
    with pytest.raises(ValueError, match="min_pxcor"):
        other.create_patches(2, 1, 0, 1)


def test_ask_over_patches_uses_snapshot_and_updates_state():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 0, heat=0)
    visited = []

    def warm(patch):
        visited.append((patch.pxcor, patch.pycor))
        patch["heat"] += 1
        if patch.pxcor == 0:
            world.create_turtles(1, breed="marker")

    world.ask(world.patches, warm)

    assert visited == [(0, 0), (1, 0)]
    assert [p["heat"] for p in world.patches.ordered()] == [1, 1]
    assert len(world.turtles.with_breed("marker")) == 1


def test_patch_neighbors_are_bounded_and_ordered():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1)
    center = world.patch_at(0, 0)
    corner = world.patch_at(-1, -1)

    assert [(p.pxcor, p.pycor) for p in center.neighbors4()] == [
        (0, -1),
        (-1, 0),
        (1, 0),
        (0, 1),
    ]
    assert [(p.pxcor, p.pycor) for p in center.neighbors()] == [
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (1, 0),
        (-1, 1),
        (0, 1),
        (1, 1),
    ]
    assert [(p.pxcor, p.pycor) for p in corner.neighbors4()] == [
        (0, -1),
        (-1, 0),
    ]
    assert [(p.pxcor, p.pycor) for p in corner.neighbors()] == [
        (0, -1),
        (-1, 0),
        (0, 0),
    ]


def test_patch_neighbor_validation_fails_clearly():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 1)
    other = NetLogoWorld(seed=0, schedule="sequential")
    other.create_patches(0, 0, 0, 0)

    with pytest.raises(ValueError, match="NetLogoPatch"):
        world.patch_neighbors4(object())
    with pytest.raises(ValueError, match="same NetLogoWorld"):
        world.patch_neighbors(other.patch_at(0, 0))


def test_netlogo_patch_neighbors_gate_passes_with_bounded_boundary():
    ok, message = netlogo_semantics.netlogo_patch_neighbors_gate()

    assert ok is True
    assert "bounded patch neighbors" in message
    assert "no wrapping" in message


def test_turtles_here_returns_patch_local_agentset_and_updates_after_setxy():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 1)
    a, b = world.create_turtles(2, breed="people").ordered()
    wolf = world.create_turtles(1, breed="wolf").ordered()[0]
    a.setxy(1, 1)
    b.setxy(1, 1)
    wolf.setxy(0, 0)
    patch = world.patch_at(1, 1)

    occupants = patch.turtles_here()

    assert isinstance(occupants, netlogo_semantics.NetLogoAgentSet)
    assert [t.id for t in occupants.ordered()] == [a.id, b.id]
    assert len(occupants.with_breed("people")) == 2
    assert len(occupants.with_breed("wolf")) == 0

    b.setxy(0, 0)

    assert [t.id for t in patch.turtles_here().ordered()] == [a.id]
    assert [t.id for t in world.patch_at(0, 0).turtles_here().ordered()] == [b.id, wolf.id]


def test_turtles_on_patch_validation_fails_clearly():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 0, 0, 0)
    other = NetLogoWorld(seed=0, schedule="sequential")
    other.create_patches(0, 0, 0, 0)

    with pytest.raises(ValueError, match="NetLogoPatch"):
        world.turtles_on(object())
    with pytest.raises(ValueError, match="same NetLogoWorld"):
        world.turtles_on(other.patch_at(0, 0))


def test_netlogo_turtles_on_patch_gate_passes_with_scan_boundary():
    ok, message = netlogo_semantics.netlogo_turtles_on_patch_gate()

    assert ok is True
    assert "patch-local turtle aggregation" in message
    assert "scan-based" in message


def test_patch_sprout_creates_turtles_at_patch_coordinate():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 1)
    patch = world.patch_at(1, 0)

    sprouted = patch.sprout(2, breed="seedlings", energy=4, xcor=0, ycor=0)

    assert isinstance(sprouted, netlogo_semantics.NetLogoAgentSet)
    assert len(sprouted) == 2
    assert [(t.xcor, t.ycor) for t in sprouted.ordered()] == [(1, 0), (1, 0)]
    assert [t.breed for t in sprouted.ordered()] == ["seedlings", "seedlings"]
    assert [t["energy"] for t in sprouted.ordered()] == [4, 4]
    assert patch.turtles_here().ordered() == sprouted.ordered()


def test_sprout_validation_fails_clearly():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 0, 0, 0)
    patch = world.patch_at(0, 0)
    other = NetLogoWorld(seed=0, schedule="sequential")
    other.create_patches(0, 0, 0, 0)

    with pytest.raises(ValueError, match="NetLogoPatch"):
        world.sprout(object(), 1)
    with pytest.raises(ValueError, match="same NetLogoWorld"):
        world.sprout(other.patch_at(0, 0), 1)
    with pytest.raises(ValueError, match="integer"):
        patch.sprout(True)
    with pytest.raises(ValueError, match="non-negative"):
        patch.sprout(-1)


def test_netlogo_sprout_gate_passes_with_minimal_boundary():
    ok, message = netlogo_semantics.netlogo_sprout_gate()

    assert ok is True
    assert "minimal sprout" in message
    assert "not full NetLogo command execution" in message


def test_radius_queries_return_bounded_patches_and_turtles_in_world_order():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1)
    a, b, c = world.create_turtles(3, breed="people").ordered()
    b.setxy(1, 0)
    c.setxy(1, 1)
    center = world.patch_at(0, 0)

    assert [(p.pxcor, p.pycor) for p in center.patches_in_radius(0)] == [(0, 0)]
    assert [(p.pxcor, p.pycor) for p in center.patches_in_radius(1)] == [
        (0, -1),
        (-1, 0),
        (0, 0),
        (1, 0),
        (0, 1),
    ]
    assert [t.id for t in center.turtles_in_radius(1).ordered()] == [a.id, b.id]
    assert [t.id for t in a.turtles_in_radius(1).ordered()] == [a.id, b.id]
    assert [(p.pxcor, p.pycor) for p in c.patches_in_radius(1)] == [
        (1, 0),
        (0, 1),
        (1, 1),
    ]

    c.setxy(0, 1)

    assert [t.id for t in center.turtles_in_radius(1).ordered()] == [a.id, b.id, c.id]


def test_radius_query_validation_fails_clearly():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 1)
    patch = world.patch_at(0, 0)
    other = NetLogoWorld(seed=0, schedule="sequential")
    other.create_patches(0, 0, 0, 0)

    with pytest.raises(ValueError, match="radius"):
        patch.patches_in_radius(True)
    with pytest.raises(ValueError, match="radius"):
        patch.turtles_in_radius(-1)
    with pytest.raises(ValueError, match="radius"):
        patch.patches_in_radius(0.5)
    with pytest.raises(ValueError, match="NetLogoPatch or NetLogoTurtle"):
        world.patches_in_radius(object(), 1)
    with pytest.raises(ValueError, match="same NetLogoWorld"):
        world.turtles_in_radius(other.patch_at(0, 0), 1)


def test_netlogo_radius_query_gate_passes_with_bounded_boundary():
    ok, message = netlogo_semantics.netlogo_radius_query_gate()

    assert ok is True
    assert "bounded radius query" in message
    assert "not NetLogo in-radius parsing" in message


def test_diffuse_patch_scalar_updates_simultaneously_over_bounded_neighbors():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1, heat=0.0)
    world.patch_at(0, 0)["heat"] = 80.0

    world.diffuse_patch_scalar("heat", 0.5)

    assert world.patch_at(0, 0)["heat"] == pytest.approx(40.0)
    assert sorted(p["heat"] for p in world.patch_at(0, 0).neighbors()) == [
        pytest.approx(5.0)
    ] * 8
    assert sum(p["heat"] for p in world.patches.ordered()) == pytest.approx(80.0)


def test_diffuse_patch_scalar_keeps_corner_mass_inside_bounded_grid():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 1, heat=0.0)
    corner = world.patch_at(0, 0)
    corner["heat"] = 30.0

    world.diffuse_patch_scalar("heat", 0.3)

    assert corner["heat"] == pytest.approx(21.0)
    assert [p["heat"] for p in corner.neighbors()] == [
        pytest.approx(3.0),
        pytest.approx(3.0),
        pytest.approx(3.0),
    ]
    assert sum(p["heat"] for p in world.patches.ordered()) == pytest.approx(30.0)


def test_diffuse_patch_scalar_validation_fails_clearly():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 1, heat=0.0)

    with pytest.raises(ValueError, match="patch variable"):
        world.diffuse_patch_scalar("", 0.5)
    with pytest.raises(ValueError, match="diffusion fraction"):
        world.diffuse_patch_scalar("heat", True)
    with pytest.raises(ValueError, match="diffusion fraction"):
        world.diffuse_patch_scalar("heat", -0.1)
    with pytest.raises(ValueError, match="diffusion fraction"):
        world.diffuse_patch_scalar("heat", 1.1)

    world.patch_at(0, 0)["heat"] = "hot"
    with pytest.raises(ValueError, match="numeric"):
        world.diffuse_patch_scalar("heat", 0.5)

    world.patch_at(0, 0)["heat"] = True
    with pytest.raises(ValueError, match="numeric"):
        world.diffuse_patch_scalar("heat", 0.5)


def test_netlogo_diffuse_gate_passes_with_bounded_boundary():
    ok, message = netlogo_semantics.netlogo_diffuse_gate()

    assert ok is True
    assert "bounded scalar diffusion" in message
    assert "no wrapping" in message


def test_other_agentset_excludes_self_and_preserves_order():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1)
    a, b, c = world.create_turtles(3, breed="people").ordered()
    b.setxy(1, 0)
    c.setxy(0, 1)

    assert [t.id for t in world.turtles.other_than(a).ordered()] == [b.id, c.id]
    assert [t.id for t in a.turtles_in_radius(1).ordered()] == [a.id, b.id, c.id]
    assert [t.id for t in a.other_turtles_in_radius(1).ordered()] == [b.id, c.id]

    c.setxy(1, 1)
    assert [t.id for t in a.other_turtles_in_radius(1).ordered()] == [b.id]


def test_other_agentset_validation_fails_clearly():
    world = NetLogoWorld(seed=0, schedule="sequential")
    a = world.create_turtles(1, breed="people").ordered()[0]
    other = NetLogoWorld(seed=0, schedule="sequential")
    outsider = other.create_turtles(1, breed="people").ordered()[0]

    with pytest.raises(ValueError, match="NetLogoTurtle"):
        world.turtles.other_than(object())
    with pytest.raises(ValueError, match="same NetLogoWorld"):
        world.turtles.other_than(outsider)

    assert world.turtles.other_than(a).ordered() == []


def test_netlogo_other_agentset_gate_passes_with_exclude_self_boundary():
    ok, message = netlogo_semantics.netlogo_other_agentset_gate()

    assert ok is True
    assert "exclude-self agentset" in message
    assert "not general NetLogo agentset parsing" in message


def test_turtles_and_patches_remain_distinct_agentsets():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 0, 0, 0, terrain="grass")
    world.create_turtles(2, breed="people")

    assert len(world.patches) == 1
    assert len(world.turtles) == 2
    assert all(isinstance(p, netlogo_semantics.NetLogoPatch) for p in world.patches)


def test_turtle_setxy_and_patch_here_bind_turtles_to_patch_grid():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1, visited=0)
    turtle = world.create_turtles(1, breed="people").ordered()[0]

    assert (turtle.xcor, turtle.ycor) == (0, 0)
    assert (turtle["xcor"], turtle["ycor"]) == (0, 0)
    assert turtle.patch_here() is world.patch_at(0, 0)

    assert turtle.setxy(1, -1) is turtle
    assert (turtle.xcor, turtle.ycor) == (1, -1)
    assert (turtle["xcor"], turtle["ycor"]) == (1, -1)
    patch = turtle.patch_here()
    patch["visited"] += 1

    assert (patch.pxcor, patch.pycor) == (1, -1)
    assert world.patch_at(1, -1)["visited"] == 1


def test_turtle_position_validation_fails_clearly():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 1)
    turtle = world.create_turtles(1, breed="people").ordered()[0]

    with pytest.raises(ValueError, match="xcor"):
        turtle.setxy(True, 0)
    with pytest.raises(ValueError, match="ycor"):
        turtle.setxy(0, 0.5)
    with pytest.raises(ValueError, match="patch not found"):
        turtle.setxy(2, 0)

    assert (turtle.xcor, turtle.ycor) == (0, 0)


def test_netlogo_turtle_patch_position_gate_passes_with_integer_only_boundary():
    ok, message = netlogo_semantics.netlogo_turtle_patch_position_gate()

    assert ok is True
    assert "integer-only turtle position" in message
    assert "not full NetLogo movement" in message


def test_cardinal_heading_and_fd_move_over_bounded_patch_grid():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1)
    turtle = world.create_turtles(1, breed="people").ordered()[0]

    assert turtle.heading == 0
    assert turtle["heading"] == 0

    assert turtle.fd() is turtle
    assert (turtle.xcor, turtle.ycor) == (0, 1)
    assert turtle.patch_here() is world.patch_at(0, 1)
    assert turtle.patch_here().turtles_here().ordered() == [turtle]

    assert turtle.rt(90) is turtle
    assert turtle.heading == 90
    assert turtle.fd(1) is turtle
    assert (turtle.xcor, turtle.ycor) == (1, 1)

    turtle.lt(180).fd(1)
    assert turtle.heading == 270
    assert (turtle.xcor, turtle.ycor) == (0, 1)

    turtle.set_heading(180).fd(2)
    assert (turtle.heading, turtle["heading"]) == (180, 180)
    assert (turtle.xcor, turtle.ycor) == (0, -1)

    turtle.set_heading(450)
    assert turtle.heading == 90


def test_heading_movement_validation_fails_without_partial_move():
    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1)
    turtle = world.create_turtles(1, breed="people").ordered()[0]

    with pytest.raises(ValueError, match="heading"):
        turtle.set_heading(45)
    with pytest.raises(ValueError, match="heading"):
        turtle.set_heading(True)
    with pytest.raises(ValueError, match="turn degrees"):
        turtle.rt(45)
    with pytest.raises(ValueError, match="turn degrees"):
        turtle.lt(0.5)
    with pytest.raises(ValueError, match="forward distance"):
        turtle.fd(True)
    with pytest.raises(ValueError, match="forward distance"):
        turtle.fd(0)

    turtle.set_heading(270)
    with pytest.raises(ValueError, match="patch not found"):
        turtle.fd(2)

    assert (turtle.xcor, turtle.ycor) == (0, 0)
    assert turtle.heading == 270


def test_netlogo_heading_movement_gate_passes_with_cardinal_boundary():
    ok, message = netlogo_semantics.netlogo_heading_movement_gate()

    assert ok is True
    assert "cardinal heading movement" in message
    assert "not full NetLogo movement" in message


def test_link_creation_lookup_and_state_are_stable():
    world = NetLogoWorld(seed=0, schedule="sequential")
    a, b, _ = world.create_turtles(3, breed="people").ordered()

    link = world.create_link(a, b, weight=2)

    assert isinstance(link, netlogo_semantics.NetLogoLink)
    assert link.end1 is a
    assert link.end2 is b
    assert link.directed is False
    assert link.breed == "links"
    assert link["weight"] == 2
    link["weight"] = 3
    assert link.get("weight") == 3
    assert world.link_between(a, b) is link
    assert world.link_between(b, a) is link
    assert world.links.ordered() == [link]


def test_undirected_duplicate_links_fail_regardless_of_endpoint_order():
    world = NetLogoWorld(seed=0, schedule="sequential")
    a, b = world.create_turtles(2, breed="people").ordered()
    world.create_link(a, b)

    with pytest.raises(ValueError, match="link already exists"):
        world.create_link(a, b)
    with pytest.raises(ValueError, match="link already exists"):
        world.create_link(b, a)


def test_directed_links_use_exact_order_and_allow_reverse_direction():
    world = NetLogoWorld(seed=0, schedule="sequential")
    a, b = world.create_turtles(2, breed="people").ordered()

    ab = world.create_link(a, b, directed=True, breed="flows")
    ba = world.create_link(b, a, directed=True, breed="flows")

    assert world.link_between(a, b, directed=True) is ab
    assert world.link_between(b, a, directed=True) is ba
    assert world.links.with_breed("flows").ordered() == [ab, ba]


def test_link_validation_rejects_invalid_cross_world_and_self_links():
    world = NetLogoWorld(seed=0, schedule="sequential")
    other = NetLogoWorld(seed=0, schedule="sequential")
    a, b = world.create_turtles(2, breed="people").ordered()
    outsider = other.create_turtles(1, breed="people").ordered()[0]

    with pytest.raises(ValueError, match="NetLogoTurtle"):
        world.create_link(a, object())
    with pytest.raises(ValueError, match="same NetLogoWorld"):
        world.create_link(a, outsider)
    with pytest.raises(ValueError, match="self-link"):
        world.create_link(a, a)
    with pytest.raises(ValueError, match="link not found"):
        world.link_between(a, b)


def test_ask_over_links_uses_snapshot_and_updates_state():
    world = NetLogoWorld(seed=0, schedule="sequential")
    a, b, c = world.create_turtles(3, breed="people").ordered()
    ab = world.create_link(a, b, traversals=0)
    bc = world.create_link(b, c, traversals=0)
    visited = []

    def mark(link):
        visited.append((link.end1.id, link.end2.id))
        link["traversals"] += 1
        if link is ab:
            with pytest.raises(ValueError, match="link already exists"):
                world.create_link(b, a)

    world.ask(world.links, mark)

    assert visited == [(a.id, b.id), (b.id, c.id)]
    assert [link["traversals"] for link in world.links.ordered()] == [1, 1]
    assert world.links.ordered() == [ab, bc]


def test_link_neighbors_return_undirected_neighbors_in_link_order():
    world = NetLogoWorld(seed=0, schedule="sequential")
    a, b, c, d = world.create_turtles(4, breed="people").ordered()
    world.create_link(a, b)
    world.create_link(c, a)
    world.create_link(a, d, directed=True)

    assert world.link_neighbors(a) == [b, c]
    assert world.link_neighbors(b) == [a]
    assert world.link_neighbors(d) == []
