"""ABM Auto Runtime — standalone ``Grid`` + ``Spot`` (ADR-009 Phase 4, Stage C).

Faithful, dependency-free reimplementation of Melodie's
``MelodieInfra.core.grid`` Grid/Spot — no Melodie import. Byte-exactness is
preserved by following the exact algorithm: the ``_convert_to_1d`` /
``_num_to_2d_coor`` coordinate maps (including Melodie's width/height
asymmetry), the ``_empty_spots`` *set* add/remove order (so ``get_empty_spots``
iteration order matches), the dx/dy neighbour-enumeration + string-keyed cache,
and Python's GLOBAL ``random`` for ``find_empty_spot`` / ``rand_move_agent``
(exactly what ``MelodieInfra.core.api`` binds — ``random.randint`` /
``random.random``) so the model's ``random.seed(...)`` drives them identically.

ABM Auto overrides retained on top: ``width`` / ``height`` as properties, an
injected ``_agent_list_ref``, and a ``get_neighbors`` that resolves the raw
``(category, id)`` tuples to GridAgent objects.
"""
from __future__ import annotations

import random
from math import floor
from typing import Any, Dict, List, Optional, Set, Tuple

from abm_auto.runtime._agent import GridAgent, GridItem


class Spot(GridItem):
    def __init__(self, spot_id: int, grid: "Grid", x: int = 0, y: int = 0) -> None:
        super().__init__(spot_id, grid, x, y)
        self.grid = grid
        self.colormap = 0

    def get_spot_agents(self):
        return self.grid.get_spot_agents(self)

    def get_style(self):
        return {"backgroundColor": "#ffffff"}


class Grid:
    """Discrete 2D space: a width×height array of ``Spot``s, each holding agents."""

    def __init__(self, spot_cls=Spot, scenario=None) -> None:
        self._width = -1
        self._height = -1
        self._wrap = False
        self._caching = True
        self._multi = False
        self._spot_cls = spot_cls
        self._existed_agents: Dict[str, Dict[int, Tuple[int, int]]] = {}
        self._agent_ids: Dict[str, List[Set[int]]] = {}
        self._spots: list = []
        self.scenario = scenario
        self._empty_spots: Set[int] = set()
        self._agent_containers: dict = {}
        self._cache: dict = {}
        # ABM Auto: injected by Model.create_grid() for zero-arg neighbour lookup
        self._agent_list_ref: Optional[Any] = None

    # ── ABM Auto public dimensions (properties, not Melodie's methods) ────────

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    # ── construction ─────────────────────────────────────────────────────────

    def init_grid(self) -> None:
        SpotCls = self._spot_cls
        self._spots = [
            [SpotCls(self._convert_to_1d(x, y), self, x, y) for x in range(self._width)]
            for y in range(self._height)
        ]
        for x in range(self._width):
            for y in range(self._height):
                self._spots[y][x].setup()
                self._empty_spots.add(self._convert_to_1d(x, y))
        self._roles_list = [
            [0 for _ in range(4)] for _ in range(self._width * self._height)
        ]

    def setup_params(self, width: int, height: int, wrap=True, caching=True, multi=True) -> None:
        self._width = width
        self._height = height
        self._wrap = wrap
        self._caching = caching
        self._multi = multi
        self.init_grid()

    def setup(self) -> None:
        pass

    def _setup(self) -> None:
        self.setup()

    def add_category(self, category_name: str) -> None:
        self._agent_ids[category_name] = [set() for _ in range(self._width * self._height)]
        self._existed_agents[category_name] = {}

    # ── coordinates ──────────────────────────────────────────────────────────

    def _convert_to_1d(self, x, y):
        return x * self._height + y

    def _num_to_2d_coor(self, num: int):
        # NB: Melodie's exact (asymmetric) inverse — height for div, width for mod.
        return floor(num / self._height), num % self._width

    def _in_bounds(self, x, y):
        return (0 <= x < self._width) and (0 <= y <= self._height)

    def _bound_check(self, x, y):
        if self._wrap:
            return self.coords_wrap(x, y)
        if not (0 <= x < self._width):
            raise IndexError("grid index x was out of range")
        elif not (0 <= y <= self._height):
            raise IndexError("grid index y was out of range")
        else:
            return x, y

    def coords_wrap(self, x, y):
        x_wrapped, y_wrapped = x % self._width, y % self._height
        x_wrapped = x_wrapped if x_wrapped >= 0 else self._width + x_wrapped
        y_wrapped = y_wrapped if y_wrapped >= 0 else self._height + y_wrapped
        return x_wrapped, y_wrapped

    # ── spots ────────────────────────────────────────────────────────────────

    def get_spot(self, x, y) -> "Spot":
        x, y = self._bound_check(x, y)
        return self._spots[y][x]

    def get_agent_ids(self, category: str, x: int, y: int) -> "Set[int]":
        return self._agent_ids[category][self._convert_to_1d(x, y)]

    def _get_category_of_agents(self, category_name: str):
        return self._existed_agents[category_name]

    # ── neighbourhood ────────────────────────────────────────────────────────

    def _get_neighbor_positions(self, x, y, radius: int = 1, moore=True, except_self=True):
        x, y = self._bound_check(x, y)
        s = f"{except_self}+{moore}+{radius}+{x}+{y}"
        if s not in self._cache:
            neighbors = []
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if not moore and abs(dx) + abs(dy) > radius:
                        continue
                    if not self._wrap and not self._in_bounds(x + dx, y + dy):
                        continue
                    if dx == 0 and dy == 0 and except_self:
                        continue
                    neighbors.append(self._bound_check(x + dx, y + dy))
            self._cache[s] = neighbors
            return neighbors
        return self._cache[s]

    def _get_neighborhood(self, x, y, radius=1, moore=True, except_self=True):
        return [self.get_spot(px, py) for (px, py) in
                self._get_neighbor_positions(x, y, radius, moore, except_self)]

    def get_agent_neighborhood(self, agent, radius=1, moore=True, except_self=True):
        return self._get_neighborhood(agent.x, agent.y, radius, moore, except_self)

    def get_spot_neighborhood(self, spot, radius=1, moore=True, except_self=True):
        return self._get_neighborhood(spot.x, spot.y, radius, moore, except_self)

    # ── agent placement ──────────────────────────────────────────────────────

    def add_agent(self, agent: GridAgent) -> None:
        if not isinstance(agent, GridAgent):
            raise TypeError(f"agent must be a {GridAgent.__name__}")
        agent.grid = self
        self._add_agent(agent.id, agent.category, agent.x, agent.y)

    def _add_agent(self, agent_id: int, category: str, x: int, y: int) -> None:
        x, y = self._bound_check(x, y)
        if category not in self._existed_agents:
            self._existed_agents[category] = {}
        if category not in self._agent_ids:
            self._agent_ids[category] = [set() for _ in range(self._width * self._height)]
        category_of_agents = self._get_category_of_agents(category)
        if agent_id in category_of_agents:
            raise ValueError(f"Agent id {agent_id} already exists on grid!")
        pos_1d = self._convert_to_1d(x, y)
        if agent_id in self._agent_ids[category][pos_1d]:
            raise ValueError(f"Agent id {agent_id} already exists at {(x, y)}!")
        self._agent_ids[category][pos_1d].add(agent_id)
        self._existed_agents[category][agent_id] = (x, y)
        if pos_1d in self._empty_spots:
            self._empty_spots.remove(pos_1d)

    def _remove_agent(self, agent_id: int, category: str, x: int, y: int) -> None:
        x, y = self._bound_check(x, y)
        category_of_agents = self._get_category_of_agents(category)
        if agent_id not in category_of_agents.keys():
            raise ValueError(f"Agent id {agent_id} does not exist on grid!")
        pos_1d = self._convert_to_1d(x, y)
        if agent_id not in self._existed_agents[category]:
            raise ValueError("Agent does not exist on the grid!")
        if agent_id not in self._agent_ids[category][pos_1d]:
            raise IndexError("agent_id does not exist on such coordinate.")
        self._agent_ids[category][pos_1d].remove(agent_id)
        self._existed_agents[category].pop(agent_id)
        if len(self._get_spot_agents(pos_1d)) == 0:
            self._empty_spots.add(pos_1d)

    def remove_agent(self, agent: GridAgent) -> None:
        source_x, source_y = self.get_agent_pos(agent.id, agent.category)
        self._remove_agent(agent.id, agent.category, source_x, source_y)

    def move_agent(self, agent: GridAgent, target_x, target_y) -> None:
        source_x, source_y = self.get_agent_pos(agent.id, agent.category)
        self._remove_agent(agent.id, agent.category, source_x, source_y)
        self._add_agent(agent.id, agent.category, target_x, target_y)
        agent.x, agent.y = target_x, target_y

    def get_agent_pos(self, agent_id: int, category: str) -> Tuple[int, int]:
        return self._existed_agents[category][agent_id]

    # ── spot agents ──────────────────────────────────────────────────────────

    def get_spot_agents(self, spot: Spot):
        return self._get_spot_agents(spot.id)

    def _get_spot_agents(self, spot_id: int):
        result = []
        for category, spot_set_list in self._agent_ids.items():
            for agent_id in spot_set_list[spot_id]:
                result.append((category, agent_id))
        return result

    # ── empty spots ──────────────────────────────────────────────────────────

    def get_empty_spots(self):
        return [self._num_to_2d_coor(p) for p in self._empty_spots]

    def find_empty_spot(self):
        rand_value = random.randint(0, len(self._empty_spots) - 1)
        i = 0
        for item in self._empty_spots:
            if i == rand_value:
                return self._num_to_2d_coor(item)
            i += 1

    # ── locations / movement ─────────────────────────────────────────────────

    def setup_agent_locations(self, category, initial_placement: str = "direct") -> None:
        self._add_agent_container(category, initial_placement.lower())

    def _add_agent_container(self, category, initial_placement) -> None:
        assert category is not None, "Agent container was None"
        first = category[0]
        category_id = first.category
        assert category_id not in self._agent_containers, f"Category {category_id} already existed!"
        self._agent_containers[category_id] = category
        assert initial_placement in ("random_single", "direct"), \
            f"Invalid initial placement {initial_placement!r}"
        if initial_placement == "random_single":
            for agent in category:
                pos = self.find_empty_spot()
                agent.x = pos[0]
                agent.y = pos[1]
                self.add_agent(agent)
        else:  # direct
            for agent in category:
                self.add_agent(agent)

    def rand_move_agent(self, agent: GridAgent, category, range_x, range_y):
        source_x = agent.x
        source_y = agent.y
        self._remove_agent(agent.id, category, source_x, source_y)
        dx = floor(random.random() * (2 * range_x + 1)) - range_x
        dy = floor(random.random() * (2 * range_y + 1)) - range_y
        target_x = source_x + dx
        target_y = source_y + dy
        self._add_agent(agent.id, category, target_x, target_y)
        return self.coords_wrap(target_x, target_y)

    def set_spot_property(self, attr_name: str, array_2d) -> None:
        for y, row in enumerate(array_2d):
            for x, value in enumerate(row):
                setattr(self.get_spot(x, y), attr_name, value)

    def get_agent_container(self, category_id):
        ret = self._agent_containers.get(category_id)
        assert ret is not None, f"Agent list for category {category_id} not registered!"
        return ret

    @property
    def agent_categories(self):
        return set(self._existed_agents.keys())

    # ── ABM Auto neighbour API (resolve raw tuples → agent objects) ───────────

    def get_neighbors(self, agent, radius=1, moore=True, except_self=True,
                      agent_list: Any = None, return_agents: bool = True):
        """Neighbours of *agent*: GridAgent objects by default, or raw
        ``(category, id)`` tuples with ``return_agents=False`` (Melodie's shape)."""
        raw = []
        for (px, py) in self._get_neighbor_positions(agent.x, agent.y, radius, moore, except_self):
            raw.extend(self._get_spot_agents(self.get_spot(px, py).id))
        if not return_agents:
            return raw
        effective_list = agent_list if agent_list is not None else self._agent_list_ref
        if effective_list is None:
            raise ValueError(
                "ABM Auto Grid.get_neighbors(): no agent_list available. Use "
                "'from abm_auto.runtime import Model' (auto-injects), or pass "
                "agent_list=self.agents."
            )
        result = []
        for item in raw:
            if isinstance(item, tuple):
                _, agent_id = item
                result.append(effective_list[agent_id])
            else:
                result.append(item)
        return result


__all__ = ["Grid", "Spot"]
