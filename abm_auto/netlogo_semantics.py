"""Small NetLogo semantic cells on top of the neutral ABM platform.

This module is not a NetLogo interpreter. It provides the first native semantic
cell needed by the coverage map: turtles, breed-filtered agentsets, ask over a
snapshot, stateful patches, minimal links, explicit ticks, globals, and monitor
collection.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from abm_auto._platform import Agent, AgentModel


_PATCH_NEIGHBORS4_OFFSETS = [(0, -1), (-1, 0), (1, 0), (0, 1)]
_PATCH_NEIGHBORS_OFFSETS = [
    (-1, -1),
    (0, -1),
    (1, -1),
    (-1, 0),
    (1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
]
_CARDINAL_DELTAS = {
    0: (0, 1),
    90: (1, 0),
    180: (0, -1),
    270: (-1, 0),
}


def _require_int_coord(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _normalize_cardinal_heading(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("heading must be an integer multiple of 90")
    if value % 90 != 0:
        raise ValueError("heading must be an integer multiple of 90")
    return value % 360


def _require_turn_degrees(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("turn degrees must be an integer multiple of 90")
    if value % 90 != 0:
        raise ValueError("turn degrees must be an integer multiple of 90")
    return value


def _require_forward_distance(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("forward distance must be a positive integer")
    if value <= 0:
        raise ValueError("forward distance must be a positive integer")
    return value


def _require_radius(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("radius must be a non-negative integer")
    if value < 0:
        raise ValueError("radius must be a non-negative integer")
    return value


def _require_selection_count(n: Any) -> int:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be a non-negative integer")
    if n < 0:
        raise ValueError("n must be a non-negative integer")
    return n


def _require_patch_variable_name(name: Any) -> str:
    if not isinstance(name, str) or not name:
        raise ValueError("patch variable name must be a non-empty string")
    return name


def _require_diffusion_fraction(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("diffusion fraction must be a number in [0, 1]")
    fraction = float(value)
    if fraction < 0.0 or fraction > 1.0:
        raise ValueError("diffusion fraction must be a number in [0, 1]")
    return fraction


def _require_numeric_patch_value(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"patch variable {name!r} must be numeric")
    return float(value)


class NetLogoTurtle(Agent):
    """A minimal turtle-like agent with a breed label and dynamic state."""

    def __init__(
        self,
        agent_id: int,
        model: "NetLogoWorld",
        *,
        breed: str = "turtles",
        **state: Any,
    ) -> None:
        super().__init__(agent_id, model)
        self.breed = str(breed)
        raw_state = dict(state)
        self.xcor = _require_int_coord("xcor", raw_state.pop("xcor", 0))
        self.ycor = _require_int_coord("ycor", raw_state.pop("ycor", 0))
        self.heading = _normalize_cardinal_heading(raw_state.pop("heading", 0))
        raw_state["xcor"] = self.xcor
        raw_state["ycor"] = self.ycor
        raw_state["heading"] = self.heading
        self.state = raw_state

    def __getitem__(self, name: str) -> Any:
        return self.state[name]

    def __setitem__(self, name: str, value: Any) -> None:
        self.state[name] = value

    def get(self, name: str, default: Any = None) -> Any:
        return self.state.get(name, default)

    def set(self, name: str, value: Any) -> "NetLogoTurtle":
        self.state[name] = value
        return self

    def setxy(self, xcor: int, ycor: int) -> "NetLogoTurtle":
        xcor = _require_int_coord("xcor", xcor)
        ycor = _require_int_coord("ycor", ycor)
        self.model.patch_at(xcor, ycor)
        self.xcor = xcor
        self.ycor = ycor
        self.state["xcor"] = xcor
        self.state["ycor"] = ycor
        return self

    def patch_here(self) -> "NetLogoPatch":
        return self.model.patch_at(self.xcor, self.ycor)

    def set_heading(self, heading: int) -> "NetLogoTurtle":
        self.heading = _normalize_cardinal_heading(heading)
        self.state["heading"] = self.heading
        return self

    def rt(self, degrees: int) -> "NetLogoTurtle":
        degrees = _require_turn_degrees(degrees)
        return self.set_heading(self.heading + degrees)

    def lt(self, degrees: int) -> "NetLogoTurtle":
        degrees = _require_turn_degrees(degrees)
        return self.set_heading(self.heading - degrees)

    def fd(self, distance: int = 1) -> "NetLogoTurtle":
        distance = _require_forward_distance(distance)
        dx, dy = _CARDINAL_DELTAS[self.heading]
        return self.setxy(self.xcor + dx * distance, self.ycor + dy * distance)

    def patches_in_radius(self, radius: int) -> "NetLogoPatchSet":
        return self.model.patches_in_radius(self, radius)

    def turtles_in_radius(self, radius: int) -> "NetLogoAgentSet":
        return self.model.turtles_in_radius(self, radius)

    def other_turtles_in_radius(self, radius: int) -> "NetLogoAgentSet":
        return self.turtles_in_radius(radius).other_than(self)

    def step(self) -> None:
        pass


class NetLogoLink(Agent):
    """A minimal stateful NetLogo link between two turtles."""

    def __init__(
        self,
        agent_id: int,
        model: "NetLogoWorld",
        *,
        end1: NetLogoTurtle,
        end2: NetLogoTurtle,
        directed: bool = False,
        breed: str = "links",
        **state: Any,
    ) -> None:
        super().__init__(agent_id, model)
        self.end1 = end1
        self.end2 = end2
        self.directed = bool(directed)
        self.breed = str(breed)
        self.state = dict(state)

    def __getitem__(self, name: str) -> Any:
        return self.state[name]

    def __setitem__(self, name: str, value: Any) -> None:
        self.state[name] = value

    def get(self, name: str, default: Any = None) -> Any:
        return self.state.get(name, default)

    def set(self, name: str, value: Any) -> "NetLogoLink":
        self.state[name] = value
        return self

    def step(self) -> None:
        pass


class NetLogoAgentSet:
    """Snapshot-capable turtle collection with NetLogo-style filters."""

    def __init__(self, model: "NetLogoWorld", agents: Iterable[NetLogoTurtle]) -> None:
        self.model = model
        self._agents = list(agents)

    def __len__(self) -> int:
        return len(self._agents)

    def __iter__(self) -> Iterator[NetLogoTurtle]:
        return iter(self.ordered())

    def snapshot(self) -> list[NetLogoTurtle]:
        return list(self._agents)

    def ordered(self) -> list[NetLogoTurtle]:
        return self.model._order_for_ask(self._agents)

    def where(self, predicate: Callable[[NetLogoTurtle], bool]) -> "NetLogoAgentSet":
        return NetLogoAgentSet(self.model, [a for a in self._agents if predicate(a)])

    def with_breed(self, breed: str) -> "NetLogoAgentSet":
        return self.where(lambda a: a.breed == breed)

    def other_than(self, turtle: NetLogoTurtle) -> "NetLogoAgentSet":
        if not isinstance(turtle, NetLogoTurtle):
            raise ValueError("other_than expects a NetLogoTurtle")
        if turtle.model is not self.model:
            raise ValueError("turtle must belong to the same NetLogoWorld")
        return NetLogoAgentSet(self.model, [a for a in self._agents if a is not turtle])

    def one_of(self) -> NetLogoTurtle:
        return self.model.one_of(self)

    def n_of(self, n: int) -> "NetLogoAgentSet":
        selected = self.model.n_of(n, self)
        if not isinstance(selected, NetLogoAgentSet):
            raise AssertionError("NetLogoAgentSet selection returned wrong type")
        return selected


class NetLogoLinkSet:
    """Snapshot-capable link collection with NetLogo-style filters."""

    def __init__(self, model: "NetLogoWorld", links: Iterable[NetLogoLink]) -> None:
        self.model = model
        self._links = list(links)

    def __len__(self) -> int:
        return len(self._links)

    def __iter__(self) -> Iterator[NetLogoLink]:
        return iter(self.ordered())

    def snapshot(self) -> list[NetLogoLink]:
        return list(self._links)

    def ordered(self) -> list[NetLogoLink]:
        return self.model._order_for_ask(self._links)

    def where(self, predicate: Callable[[NetLogoLink], bool]) -> "NetLogoLinkSet":
        return NetLogoLinkSet(self.model, [link for link in self._links if predicate(link)])

    def with_breed(self, breed: str) -> "NetLogoLinkSet":
        return self.where(lambda link: link.breed == breed)

    def one_of(self) -> NetLogoLink:
        return self.model.one_of(self)

    def n_of(self, n: int) -> "NetLogoLinkSet":
        selected = self.model.n_of(n, self)
        if not isinstance(selected, NetLogoLinkSet):
            raise AssertionError("NetLogoLinkSet selection returned wrong type")
        return selected


class NetLogoPatch(Agent):
    """A minimal stateful NetLogo patch with integer coordinates."""

    def __init__(
        self,
        agent_id: int,
        model: "NetLogoWorld",
        *,
        pxcor: int,
        pycor: int,
        **state: Any,
    ) -> None:
        super().__init__(agent_id, model)
        self.pxcor = pxcor
        self.pycor = pycor
        self.state = dict(state)

    def __getitem__(self, name: str) -> Any:
        return self.state[name]

    def __setitem__(self, name: str, value: Any) -> None:
        self.state[name] = value

    def get(self, name: str, default: Any = None) -> Any:
        return self.state.get(name, default)

    def set(self, name: str, value: Any) -> "NetLogoPatch":
        self.state[name] = value
        return self

    def neighbors4(self) -> list["NetLogoPatch"]:
        return self.model.patch_neighbors4(self)

    def neighbors(self) -> list["NetLogoPatch"]:
        return self.model.patch_neighbors(self)

    def turtles_here(self) -> NetLogoAgentSet:
        return self.model.turtles_on(self)

    def sprout(
        self,
        n: int,
        *,
        breed: str = "turtles",
        **state: Any,
    ) -> NetLogoAgentSet:
        return self.model.sprout(self, n, breed=breed, **state)

    def patches_in_radius(self, radius: int) -> "NetLogoPatchSet":
        return self.model.patches_in_radius(self, radius)

    def turtles_in_radius(self, radius: int) -> NetLogoAgentSet:
        return self.model.turtles_in_radius(self, radius)

    def step(self) -> None:
        pass


class NetLogoPatchSet:
    """Snapshot-capable patch collection with NetLogo-style filters."""

    def __init__(self, model: "NetLogoWorld", patches: Iterable[NetLogoPatch]) -> None:
        self.model = model
        self._patches = list(patches)

    def __len__(self) -> int:
        return len(self._patches)

    def __iter__(self) -> Iterator[NetLogoPatch]:
        return iter(self.ordered())

    def snapshot(self) -> list[NetLogoPatch]:
        return list(self._patches)

    def ordered(self) -> list[NetLogoPatch]:
        return self.model._order_for_ask(self._patches)

    def where(self, predicate: Callable[[NetLogoPatch], bool]) -> "NetLogoPatchSet":
        return NetLogoPatchSet(self.model, [p for p in self._patches if predicate(p)])

    def one_of(self) -> NetLogoPatch:
        return self.model.one_of(self)

    def n_of(self, n: int) -> "NetLogoPatchSet":
        selected = self.model.n_of(n, self)
        if not isinstance(selected, NetLogoPatchSet):
            raise AssertionError("NetLogoPatchSet selection returned wrong type")
        return selected


class NetLogoWorld(AgentModel):
    """Minimal observer/world context for native NetLogo-like semantic cells."""

    def __init__(
        self,
        *,
        seed: int = 0,
        schedule: str = "sequential",
        globals: dict[str, Any] | None = None,
        monitors: dict[str, Callable[["NetLogoWorld"], Any]] | None = None,
    ) -> None:
        super().__init__(seed=seed, schedule=schedule)
        self.globals = dict(globals or {})
        self._next_turtle_id = 0
        self._next_patch_id = -1
        self._next_link_id = -1_000_000
        self._patch_index: dict[tuple[int, int], NetLogoPatch] = {}
        self._link_index: dict[tuple[bool, int, int], NetLogoLink] = {}
        self._monitors: dict[str, Callable[["NetLogoWorld"], Any]] = dict(monitors or {})
        self.monitor_records: list[dict[str, Any]] = []

    @property
    def turtles(self) -> NetLogoAgentSet:
        return NetLogoAgentSet(self, [a for a in self.agents if isinstance(a, NetLogoTurtle)])

    @property
    def patches(self) -> NetLogoPatchSet:
        return NetLogoPatchSet(self, [a for a in self.agents if isinstance(a, NetLogoPatch)])

    @property
    def links(self) -> NetLogoLinkSet:
        return NetLogoLinkSet(self, [a for a in self.agents if isinstance(a, NetLogoLink)])

    def create_turtles(
        self,
        n: int,
        *,
        breed: str = "turtles",
        **state: Any,
    ) -> NetLogoAgentSet:
        if isinstance(n, bool) or not isinstance(n, int):
            raise ValueError("n must be an integer")
        if n < 0:
            raise ValueError("n must be non-negative")

        created: list[NetLogoTurtle] = []
        for _ in range(n):
            turtle = NetLogoTurtle(
                self._next_turtle_id,
                self,
                breed=breed,
                **state,
            )
            self._next_turtle_id += 1
            self.add_agent(turtle)
            created.append(turtle)
        return NetLogoAgentSet(self, created)

    def create_patches(
        self,
        min_pxcor: int,
        max_pxcor: int,
        min_pycor: int,
        max_pycor: int,
        **state: Any,
    ) -> NetLogoPatchSet:
        min_pxcor = _require_int_coord("min_pxcor", min_pxcor)
        max_pxcor = _require_int_coord("max_pxcor", max_pxcor)
        min_pycor = _require_int_coord("min_pycor", min_pycor)
        max_pycor = _require_int_coord("max_pycor", max_pycor)
        if self._patch_index:
            raise ValueError("patch grid already exists")
        if min_pxcor > max_pxcor:
            raise ValueError("min_pxcor must be <= max_pxcor")
        if min_pycor > max_pycor:
            raise ValueError("min_pycor must be <= max_pycor")

        created: list[NetLogoPatch] = []
        for pycor in range(min_pycor, max_pycor + 1):
            for pxcor in range(min_pxcor, max_pxcor + 1):
                patch = NetLogoPatch(
                    self._next_patch_id,
                    self,
                    pxcor=pxcor,
                    pycor=pycor,
                    **state,
                )
                self._next_patch_id -= 1
                self._patch_index[(pxcor, pycor)] = patch
                self.add_agent(patch)
                created.append(patch)
        return NetLogoPatchSet(self, created)

    def patch_at(self, pxcor: int, pycor: int) -> NetLogoPatch:
        pxcor = _require_int_coord("patch coordinate", pxcor)
        pycor = _require_int_coord("patch coordinate", pycor)
        try:
            return self._patch_index[(pxcor, pycor)]
        except KeyError as exc:
            raise ValueError(f"patch not found at ({pxcor}, {pycor})") from exc

    def _require_patch(self, name: str, patch: Any) -> NetLogoPatch:
        if not isinstance(patch, NetLogoPatch):
            raise ValueError(f"{name} must be a NetLogoPatch")
        if patch.model is not self:
            raise ValueError("patch must belong to the same NetLogoWorld")
        return patch

    def patch_neighbors4(self, patch: NetLogoPatch) -> list[NetLogoPatch]:
        return self._patch_neighbors_by_offsets(patch, _PATCH_NEIGHBORS4_OFFSETS)

    def patch_neighbors(self, patch: NetLogoPatch) -> list[NetLogoPatch]:
        return self._patch_neighbors_by_offsets(patch, _PATCH_NEIGHBORS_OFFSETS)

    def turtles_on(self, patch: NetLogoPatch) -> NetLogoAgentSet:
        patch = self._require_patch("patch", patch)
        return NetLogoAgentSet(
            self,
            [
                turtle
                for turtle in self.turtles.ordered()
                if (turtle.xcor, turtle.ycor) == (patch.pxcor, patch.pycor)
            ],
        )

    def sprout(
        self,
        patch: NetLogoPatch,
        n: int,
        *,
        breed: str = "turtles",
        **state: Any,
    ) -> NetLogoAgentSet:
        patch = self._require_patch("patch", patch)
        state = dict(state)
        state.pop("xcor", None)
        state.pop("ycor", None)
        created = self.create_turtles(n, breed=breed, **state)
        for turtle in created.snapshot():
            turtle.setxy(patch.pxcor, patch.pycor)
        return created

    def patches_in_radius(
        self,
        center: NetLogoPatch | NetLogoTurtle,
        radius: int,
    ) -> NetLogoPatchSet:
        cx, cy = self._center_coordinate(center)
        radius = _require_radius(radius)
        radius_squared = radius * radius
        return NetLogoPatchSet(
            self,
            [
                patch
                for patch in self.patches.ordered()
                if (patch.pxcor - cx) ** 2 + (patch.pycor - cy) ** 2 <= radius_squared
            ],
        )

    def turtles_in_radius(
        self,
        center: NetLogoPatch | NetLogoTurtle,
        radius: int,
    ) -> NetLogoAgentSet:
        cx, cy = self._center_coordinate(center)
        radius = _require_radius(radius)
        radius_squared = radius * radius
        return NetLogoAgentSet(
            self,
            [
                turtle
                for turtle in self.turtles.ordered()
                if (turtle.xcor - cx) ** 2 + (turtle.ycor - cy) ** 2 <= radius_squared
            ],
        )

    def diffuse_patch_scalar(self, name: str, fraction: float) -> "NetLogoWorld":
        name = _require_patch_variable_name(name)
        fraction = _require_diffusion_fraction(fraction)
        patches = self.patches.ordered()
        values = {
            patch: _require_numeric_patch_value(name, patch.get(name, 0.0))
            for patch in patches
        }
        next_values = {patch: value * (1.0 - fraction) for patch, value in values.items()}

        for patch, value in values.items():
            diffused = value * fraction
            neighbors = patch.neighbors()
            if not neighbors:
                next_values[patch] += diffused
                continue
            share = diffused / len(neighbors)
            for neighbor in neighbors:
                next_values[neighbor] += share

        for patch, value in next_values.items():
            patch[name] = value
        return self

    def _center_coordinate(self, center: NetLogoPatch | NetLogoTurtle) -> tuple[int, int]:
        if isinstance(center, NetLogoPatch):
            if center.model is not self:
                raise ValueError("center must belong to the same NetLogoWorld")
            return center.pxcor, center.pycor
        if isinstance(center, NetLogoTurtle):
            if center.model is not self:
                raise ValueError("center must belong to the same NetLogoWorld")
            return center.xcor, center.ycor
        raise ValueError("center must be a NetLogoPatch or NetLogoTurtle")

    def _patch_neighbors_by_offsets(
        self,
        patch: NetLogoPatch,
        offsets: Iterable[tuple[int, int]],
    ) -> list[NetLogoPatch]:
        patch = self._require_patch("patch", patch)
        neighbors: list[NetLogoPatch] = []
        for dx, dy in offsets:
            neighbor = self._patch_index.get((patch.pxcor + dx, patch.pycor + dy))
            if neighbor is not None:
                neighbors.append(neighbor)
        return neighbors

    def _require_turtle(self, name: str, turtle: Any) -> NetLogoTurtle:
        if not isinstance(turtle, NetLogoTurtle):
            raise ValueError(f"{name} must be a NetLogoTurtle")
        if turtle.model is not self:
            raise ValueError("link endpoints must belong to the same NetLogoWorld")
        return turtle

    def _link_key(
        self,
        end1: NetLogoTurtle,
        end2: NetLogoTurtle,
        directed: bool,
    ) -> tuple[bool, int, int]:
        if directed:
            return (True, end1.id, end2.id)
        low, high = sorted((end1.id, end2.id))
        return (False, low, high)

    def create_link(
        self,
        end1: NetLogoTurtle,
        end2: NetLogoTurtle,
        *,
        directed: bool = False,
        breed: str = "links",
        **state: Any,
    ) -> NetLogoLink:
        end1 = self._require_turtle("end1", end1)
        end2 = self._require_turtle("end2", end2)
        if end1 is end2:
            raise ValueError("self-link is not supported")
        directed = bool(directed)
        key = self._link_key(end1, end2, directed)
        if key in self._link_index:
            raise ValueError("link already exists")

        link = NetLogoLink(
            self._next_link_id,
            self,
            end1=end1,
            end2=end2,
            directed=directed,
            breed=breed,
            **state,
        )
        self._next_link_id -= 1
        self._link_index[key] = link
        self.add_agent(link)
        return link

    def link_between(
        self,
        end1: NetLogoTurtle,
        end2: NetLogoTurtle,
        *,
        directed: bool = False,
    ) -> NetLogoLink:
        end1 = self._require_turtle("end1", end1)
        end2 = self._require_turtle("end2", end2)
        key = self._link_key(end1, end2, bool(directed))
        try:
            return self._link_index[key]
        except KeyError as exc:
            raise ValueError("link not found") from exc

    def link_neighbors(self, turtle: NetLogoTurtle) -> list[NetLogoTurtle]:
        turtle = self._require_turtle("turtle", turtle)
        seen: set[int] = set()
        neighbors: list[NetLogoTurtle] = []
        for link in self.links.ordered():
            if link.directed:
                continue
            other = None
            if link.end1 is turtle:
                other = link.end2
            elif link.end2 is turtle:
                other = link.end1
            if other is not None and other.id not in seen:
                seen.add(other.id)
                neighbors.append(other)
        return neighbors

    def create_link_with_nearest_unlinked(
        self,
        source: NetLogoTurtle,
        candidates: NetLogoAgentSet | Iterable[NetLogoTurtle] | None = None,
        *,
        directed: bool = False,
        breed: str = "links",
        **state: Any,
    ) -> NetLogoLink | None:
        source = self._require_turtle("source", source)
        if candidates is None:
            raw_candidates = self.turtles.snapshot()
        elif isinstance(candidates, NetLogoAgentSet):
            if candidates.model is not self:
                raise ValueError("candidates must belong to the same NetLogoWorld")
            raw_candidates = candidates.snapshot()
        else:
            raw_candidates = list(candidates)

        eligible: list[NetLogoTurtle] = []
        for candidate in raw_candidates:
            if not isinstance(candidate, NetLogoTurtle):
                raise ValueError("candidate must be a NetLogoTurtle")
            if candidate.model is not self:
                raise ValueError("candidate must belong to the same NetLogoWorld")
            if candidate is source:
                continue
            if self._link_key(source, candidate, bool(directed)) in self._link_index:
                continue
            eligible.append(candidate)

        if not eligible:
            return None

        target = min(
            eligible,
            key=lambda turtle: (
                (turtle.xcor - source.xcor) ** 2 + (turtle.ycor - source.ycor) ** 2,
                turtle.id,
            ),
        )
        return self.create_link(source, target, directed=directed, breed=breed, **state)

    def one_of(
        self,
        collection: NetLogoAgentSet | NetLogoPatchSet | NetLogoLinkSet | Iterable[Any],
    ) -> Any:
        items, _factory = self._selection_items_and_factory(collection)
        if not items:
            raise ValueError("one_of expects a non-empty collection")
        return self.rng.choice(items)

    def n_of(
        self,
        n: int,
        collection: NetLogoAgentSet | NetLogoPatchSet | NetLogoLinkSet | Iterable[Any],
    ) -> NetLogoAgentSet | NetLogoPatchSet | NetLogoLinkSet | list[Any]:
        n = _require_selection_count(n)
        items, factory = self._selection_items_and_factory(collection)
        if n > len(items):
            raise ValueError("n cannot exceed collection size")
        selected = self.rng.sample(items, n)
        if factory is None:
            return selected
        return factory(selected)

    def _selection_items_and_factory(
        self,
        collection: NetLogoAgentSet | NetLogoPatchSet | NetLogoLinkSet | Iterable[Any],
    ) -> tuple[list[Any], Callable[[list[Any]], Any] | None]:
        if isinstance(collection, NetLogoAgentSet):
            if collection.model is not self:
                raise ValueError("selection collection must belong to the same NetLogoWorld")
            return collection.snapshot(), lambda items: NetLogoAgentSet(self, items)
        if isinstance(collection, NetLogoPatchSet):
            if collection.model is not self:
                raise ValueError("selection collection must belong to the same NetLogoWorld")
            return collection.snapshot(), lambda items: NetLogoPatchSet(self, items)
        if isinstance(collection, NetLogoLinkSet):
            if collection.model is not self:
                raise ValueError("selection collection must belong to the same NetLogoWorld")
            return collection.snapshot(), lambda items: NetLogoLinkSet(self, items)
        return list(collection), None

    def ask(
        self,
        agentset: NetLogoAgentSet | NetLogoPatchSet | NetLogoLinkSet,
        command: Callable[[NetLogoTurtle | NetLogoPatch | NetLogoLink], None],
    ) -> None:
        if not isinstance(agentset, (NetLogoAgentSet, NetLogoPatchSet, NetLogoLinkSet)):
            raise ValueError("ask expects a NetLogo agentset")
        snapshot = agentset.snapshot()
        for agent in self._order_for_ask(snapshot):
            command(agent)

    def tick(self, amount: int = 1) -> None:
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ValueError("tick amount must be an integer")
        if amount <= 0:
            raise ValueError("tick amount must be positive")
        self.t += amount

    def reset_ticks(self) -> None:
        self.t = 0

    def monitor(self, name: str, fn: Callable[["NetLogoWorld"], Any]) -> None:
        self._monitors[str(name)] = fn

    def collect_monitors(self) -> dict[str, Any]:
        record = {"t": self.t}
        record.update({name: fn(self) for name, fn in self._monitors.items()})
        self.monitor_records.append(record)
        return record

    def _order_for_ask(
        self,
        agents: Iterable[NetLogoTurtle | NetLogoPatch | NetLogoLink],
    ) -> list[NetLogoTurtle | NetLogoPatch | NetLogoLink]:
        ordered = list(agents)
        if self.agents.schedule == "random_order":
            self.rng.shuffle(ordered)
        return ordered


def netlogo_turtle_patch_position_gate() -> tuple[bool, str]:
    """Gate the supported integer-only turtle position over patches."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1, visited=0)
    turtle = world.create_turtles(1, breed="people").ordered()[0]

    try:
        if turtle.patch_here() is not world.patch_at(0, 0):
            return False, "default turtle position did not resolve to patch (0, 0)"
        turtle.setxy(1, -1)
        patch = turtle.patch_here()
        patch["visited"] += 1
        if (turtle.xcor, turtle.ycor) != (1, -1):
            return False, "setxy did not update turtle coordinates"
        if world.patch_at(1, -1)["visited"] != 1:
            return False, "patch_here did not return the expected patch"
        try:
            turtle.setxy(2, 0)
        except ValueError:
            pass
        else:
            return False, "setxy accepted a coordinate outside the patch grid"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo integer-only turtle position gate passed; this is not full NetLogo movement semantics.",
    )


def netlogo_patch_neighbors_gate() -> tuple[bool, str]:
    """Gate the supported bounded patch-neighbor reporters."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1)
    center = world.patch_at(0, 0)
    corner = world.patch_at(-1, -1)

    try:
        if len(center.neighbors4()) != 4:
            return False, "center patch did not have 4 bounded cardinal neighbors"
        if len(center.neighbors()) != 8:
            return False, "center patch did not have 8 bounded Moore neighbors"
        if len(corner.neighbors4()) != 2:
            return False, "corner patch cardinal neighbors were not bounded"
        if len(corner.neighbors()) != 3:
            return False, "corner patch Moore neighbors were not bounded"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo bounded patch neighbors gate passed; no wrapping or diffusion semantics are claimed.",
    )


def netlogo_turtles_on_patch_gate() -> tuple[bool, str]:
    """Gate the supported scan-based patch-local turtle aggregation."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 1)
    a, b = world.create_turtles(2, breed="people").ordered()
    wolf = world.create_turtles(1, breed="wolf").ordered()[0]
    a.setxy(1, 1)
    b.setxy(1, 1)
    wolf.setxy(0, 0)
    patch = world.patch_at(1, 1)

    try:
        if [t.id for t in patch.turtles_here().ordered()] != [a.id, b.id]:
            return False, "patch-local turtle aggregation did not find expected turtles"
        if len(patch.turtles_here().with_breed("wolf")) != 0:
            return False, "patch-local turtle aggregation ignored breed filtering"
        b.setxy(0, 0)
        if [t.id for t in patch.turtles_here().ordered()] != [a.id]:
            return False, "patch-local turtle aggregation did not reflect moved turtle"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo patch-local turtle aggregation gate passed; this is scan-based, not indexed occupancy.",
    )


def netlogo_sprout_gate() -> tuple[bool, str]:
    """Gate the supported minimal patch-origin turtle creation."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(0, 1, 0, 1)
    patch = world.patch_at(1, 0)

    try:
        sprouted = patch.sprout(2, breed="seedlings", energy=4, xcor=0, ycor=0)
        if len(sprouted) != 2:
            return False, "minimal sprout did not create the expected turtle count"
        if any((turtle.xcor, turtle.ycor) != (1, 0) for turtle in sprouted.ordered()):
            return False, "minimal sprout did not place turtles at the source patch"
        if len(patch.turtles_here().with_breed("seedlings")) != 2:
            return False, "minimal sprout was not visible through patch-local aggregation"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo minimal sprout gate passed; this is not full NetLogo command execution.",
    )


def netlogo_heading_movement_gate() -> tuple[bool, str]:
    """Gate the supported cardinal-only turtle heading and forward movement."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1)
    turtle = world.create_turtles(1, breed="people").ordered()[0]

    try:
        if turtle.heading != 0:
            return False, "new turtle did not start with heading 0"
        turtle.fd()
        if (turtle.xcor, turtle.ycor) != (0, 1):
            return False, "heading 0 did not move north"
        turtle.rt(90).fd(1)
        if (turtle.heading, turtle.xcor, turtle.ycor) != (90, 1, 1):
            return False, "right turn and east movement did not match cardinal semantics"
        turtle.lt(180).fd(1)
        if (turtle.heading, turtle.xcor, turtle.ycor) != (270, 0, 1):
            return False, "left turn and west movement did not match cardinal semantics"
        turtle.set_heading(180).fd(2)
        if (turtle.xcor, turtle.ycor) != (0, -1):
            return False, "positive integer forward distance did not move to the destination patch"
        before = (turtle.xcor, turtle.ycor)
        turtle.set_heading(270)
        try:
            turtle.fd(2)
        except ValueError:
            pass
        else:
            return False, "out-of-grid forward movement did not fail"
        if (turtle.xcor, turtle.ycor) != before:
            return False, "failed forward movement partially changed coordinates"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo cardinal heading movement gate passed; this is not full NetLogo movement semantics.",
    )


def netlogo_radius_query_gate() -> tuple[bool, str]:
    """Gate the supported bounded radius query reporters."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1)
    a, b, c = world.create_turtles(3, breed="people").ordered()
    b.setxy(1, 0)
    c.setxy(1, 1)
    center = world.patch_at(0, 0)

    try:
        if [(p.pxcor, p.pycor) for p in center.patches_in_radius(1)] != [
            (0, -1),
            (-1, 0),
            (0, 0),
            (1, 0),
            (0, 1),
        ]:
            return False, "bounded radius query returned unexpected patches"
        if [t.id for t in center.turtles_in_radius(1).ordered()] != [a.id, b.id]:
            return False, "bounded radius query returned unexpected turtles"
        c.setxy(0, 1)
        if [t.id for t in a.turtles_in_radius(1).ordered()] != [a.id, b.id, c.id]:
            return False, "bounded radius query did not reflect moved turtle"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo bounded radius query gate passed; this is not NetLogo in-radius parsing.",
    )


def netlogo_diffuse_gate() -> tuple[bool, str]:
    """Gate the supported bounded scalar patch diffusion."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1, heat=0.0)
    world.patch_at(0, 0)["heat"] = 80.0

    try:
        world.diffuse_patch_scalar("heat", 0.5)
        if world.patch_at(0, 0)["heat"] != 40.0:
            return False, "bounded scalar diffusion did not retain center mass"
        if any(p["heat"] != 5.0 for p in world.patch_at(0, 0).neighbors()):
            return False, "bounded scalar diffusion did not distribute to Moore neighbors"
        if sum(p["heat"] for p in world.patches.ordered()) != 80.0:
            return False, "bounded scalar diffusion did not conserve mass"

        edge_world = NetLogoWorld(seed=0, schedule="sequential")
        edge_world.create_patches(0, 1, 0, 1, heat=0.0)
        corner = edge_world.patch_at(0, 0)
        corner["heat"] = 30.0
        edge_world.diffuse_patch_scalar("heat", 0.3)
        if sum(p["heat"] for p in edge_world.patches.ordered()) != 30.0:
            return False, "bounded scalar diffusion leaked mass at grid edge"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo bounded scalar diffusion gate passed; no wrapping or parser semantics are claimed.",
    )


def netlogo_other_agentset_gate() -> tuple[bool, str]:
    """Gate the supported exclude-self turtle agentset behavior."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_patches(-1, 1, -1, 1)
    a, b, c = world.create_turtles(3, breed="people").ordered()
    b.setxy(1, 0)
    c.setxy(0, 1)

    try:
        if [t.id for t in world.turtles.other_than(a).ordered()] != [b.id, c.id]:
            return False, "exclude-self agentset did not preserve order"
        if [t.id for t in a.other_turtles_in_radius(1).ordered()] != [b.id, c.id]:
            return False, "exclude-self radius query returned unexpected turtles"
        c.setxy(1, 1)
        if [t.id for t in a.other_turtles_in_radius(1).ordered()] != [b.id]:
            return False, "exclude-self radius query did not reflect moved turtle"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo exclude-self agentset gate passed; this is not general NetLogo agentset parsing.",
    )


def netlogo_virus_network_setup_slice_gate() -> tuple[bool, str]:
    """Gate the supported manual Virus setup random/network slice."""

    def seeded_signature(seed: int) -> tuple[int, tuple[int, int]]:
        world = NetLogoWorld(seed=seed, schedule="sequential")
        turtles = world.create_turtles(5, breed="people")
        one = world.one_of(turtles)
        many = world.n_of(2, turtles)
        if not isinstance(many, NetLogoAgentSet):
            raise AssertionError("n_of over turtles did not return a turtle agentset")
        return one.id, tuple(t.id for t in many.ordered())

    try:
        if seeded_signature(11) != seeded_signature(11):
            return False, "seeded random selection was not stable"

        world = NetLogoWorld(seed=0, schedule="sequential")
        world.create_patches(0, 2, 0, 0)
        a, b, c = world.create_turtles(3, breed="people").ordered()
        a.setxy(0, 0)
        b.setxy(1, 0)
        c.setxy(2, 0)

        first = world.create_link_with_nearest_unlinked(a)
        second = world.create_link_with_nearest_unlinked(a)
        third = world.create_link_with_nearest_unlinked(a)
        if first is None or first.end2 is not b:
            return False, "nearest unlinked helper did not choose the nearest turtle"
        if second is None or second.end2 is not c:
            return False, "nearest unlinked helper did not skip existing links"
        if third is not None:
            return False, "nearest unlinked helper created a duplicate link"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo Virus setup slice gate passed; seeded random selection and nearest-unlinked link creation are native, but this is not NetLogo procedure execution.",
    )
