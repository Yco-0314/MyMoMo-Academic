"""ABM Auto Runtime — discrete 2D ``Grid`` + ``Spot``.

A width×height lattice of cells (``Spot``), each holding the agents that occupy
it. Agents are ``GridAgent`` objects; a cell stores them directly, so neighbour
queries return live objects with no id-to-object resolution step.

Design notes (the parts worth knowing as a caller):

* **Coordinates are row-major.** A cell at ``(x, y)`` has linear index
  ``y*width + x``; the inverse is ``divmod(idx, width)``. This is exact for any
  rectangle (square or not) and is the single source of truth for both spot
  storage and the empty-cell index.
* **Bounds are half-open**: a position is in range iff
  ``0 <= x < width and 0 <= y < height``. Out-of-range access raises
  ``IndexError`` unless the grid wraps (toroidal), in which case coordinates are
  reduced modulo the dimensions.
* **Empty cells are tracked for O(1) sampling.** ``find_empty_spot`` draws
  uniformly from a packed list of empty indices; placement/removal keep that list
  and its position map in sync with a swap-remove, so neither sampling nor update
  scans the grid.
* **Randomness is injectable and seedable.** The grid owns a ``random.Random``
  (``seed()`` to make placement reproducible); it never touches the global
  ``random`` state, so concurrent grids don't perturb each other.
* **Neighbourhoods are cached** per ``(x, y, radius, moore, except_self)`` key,
  supporting both Moore (8-cell) and von Neumann (4-cell) shapes.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from abm_auto.runtime._agent import GridAgent, GridItem


class Spot(GridItem):
    """One grid cell. Owns the list of agents currently standing on it."""

    def __init__(self, spot_id: int, grid: "Grid", x: int = 0, y: int = 0) -> None:
        super().__init__(spot_id, grid, x, y)
        self.grid = grid
        self.colormap = 0
        self._occupants: List[GridAgent] = []

    def get_spot_agents(self):
        return list(self._occupants)

    @property
    def is_empty(self) -> bool:
        return not self._occupants

    def get_style(self):
        return {"backgroundColor": "#ffffff"}


class Grid:
    """Discrete 2D space: a width×height array of ``Spot``s, each holding agents."""

    def __init__(self, spot_cls=Spot, scenario=None) -> None:
        self._spot_cls = spot_cls
        self.scenario = scenario
        self._width = -1
        self._height = -1
        self._wrap = False
        self._multi = False
        self._spots: List[Spot] = []                       # flat, row-major
        self._registry: Dict[Tuple[Any, int], GridAgent] = {}  # (category, id) → agent
        self._categories: Set[Any] = set()
        self._agent_containers: Dict[Any, Any] = {}
        self._empty: List[int] = []                        # linear indices, packed
        self._empty_at: Dict[int, int] = {}                # idx → position in _empty
        self._neighbor_cache: Dict[tuple, list] = {}
        self._rng = random.Random()
        # Back-compat hook: Model.create_grid may assign this. The redesigned
        # grid stores agent objects directly, so it is never read here.
        self._agent_list_ref: Optional[Any] = None

    # ── dimensions / rng ──────────────────────────────────────────────────────

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def seed(self, value) -> None:
        """Seed the grid's RNG so placement/movement are reproducible."""
        self._rng.seed(value)

    # ── coordinates (row-major) ───────────────────────────────────────────────

    def _to_index(self, x: int, y: int) -> int:
        return y * self._width + x

    def _to_xy(self, idx: int) -> Tuple[int, int]:
        return idx % self._width, idx // self._width

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self._width and 0 <= y < self._height

    def coords_wrap(self, x: int, y: int) -> Tuple[int, int]:
        # Python's % already yields a non-negative result for positive divisors.
        return x % self._width, y % self._height

    def _bound_check(self, x: int, y: int) -> Tuple[int, int]:
        if self._wrap:
            return self.coords_wrap(x, y)
        if not self._in_bounds(x, y):
            raise IndexError(
                f"grid position {(x, y)} out of range {self._width}x{self._height}"
            )
        return x, y

    # private aliases kept for any caller using the old internal names
    def _convert_to_1d(self, x: int, y: int) -> int:
        return self._to_index(x, y)

    def _num_to_2d_coor(self, num: int) -> Tuple[int, int]:
        return self._to_xy(num)

    # ── construction ──────────────────────────────────────────────────────────

    def init_grid(self) -> None:
        SpotCls = self._spot_cls
        n = self._width * self._height
        self._spots = [None] * n  # type: ignore[list-item]
        self._empty = []
        self._empty_at = {}
        for y in range(self._height):
            for x in range(self._width):
                idx = self._to_index(x, y)
                spot = SpotCls(idx, self, x, y)
                spot.setup()
                self._spots[idx] = spot
                self._empty_at[idx] = len(self._empty)
                self._empty.append(idx)

    def setup_params(self, width: int, height: int, wrap=True, caching=True, multi=True) -> None:
        self._width = width
        self._height = height
        self._wrap = wrap
        self._multi = multi
        self._neighbor_cache.clear()
        self.init_grid()

    def setup(self) -> None:
        pass

    def _setup(self) -> None:
        self.setup()

    def add_category(self, category_name) -> None:
        self._categories.add(category_name)

    # ── spots ─────────────────────────────────────────────────────────────────

    def get_spot(self, x, y) -> "Spot":
        x, y = self._bound_check(x, y)
        return self._spots[self._to_index(x, y)]

    def get_spot_agents(self, spot: Spot):
        return list(spot._occupants)

    def get_agent_ids(self, category, x: int, y: int) -> Set[int]:
        x, y = self._bound_check(x, y)
        spot = self._spots[self._to_index(x, y)]
        return {a.id for a in spot._occupants if a.category == category}

    # ── empty-cell bookkeeping (O(1) swap-remove) ─────────────────────────────

    def _mark_occupied(self, idx: int) -> None:
        pos = self._empty_at.pop(idx, None)
        if pos is None:
            return
        last = self._empty.pop()
        if last != idx:
            self._empty[pos] = last
            self._empty_at[last] = pos

    def _mark_empty(self, idx: int) -> None:
        if idx in self._empty_at:
            return
        self._empty_at[idx] = len(self._empty)
        self._empty.append(idx)

    def get_empty_spots(self):
        return [self._to_xy(idx) for idx in self._empty]

    def find_empty_spot(self):
        if not self._empty:
            return None
        return self._to_xy(self._rng.choice(self._empty))

    # ── neighbourhood ─────────────────────────────────────────────────────────

    def _offsets(self, radius: int, moore: bool, except_self: bool):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx == 0 and dy == 0 and except_self:
                    continue
                if not moore and abs(dx) + abs(dy) > radius:
                    continue
                yield dx, dy

    def _get_neighbor_positions(self, x, y, radius: int = 1, moore=True, except_self=True):
        x, y = self._bound_check(x, y)
        key = (x, y, radius, moore, except_self)
        cached = self._neighbor_cache.get(key)
        if cached is not None:
            return cached
        positions = []
        for dx, dy in self._offsets(radius, moore, except_self):
            nx, ny = x + dx, y + dy
            if self._wrap:
                positions.append(self.coords_wrap(nx, ny))
            elif self._in_bounds(nx, ny):
                positions.append((nx, ny))
        self._neighbor_cache[key] = positions
        return positions

    def _get_neighborhood(self, x, y, radius=1, moore=True, except_self=True):
        return [self._spots[self._to_index(px, py)]
                for (px, py) in self._get_neighbor_positions(x, y, radius, moore, except_self)]

    def get_agent_neighborhood(self, agent, radius=1, moore=True, except_self=True):
        return self._get_neighborhood(agent.x, agent.y, radius, moore, except_self)

    def get_spot_neighborhood(self, spot, radius=1, moore=True, except_self=True):
        return self._get_neighborhood(spot.x, spot.y, radius, moore, except_self)

    # ── agent placement ───────────────────────────────────────────────────────

    def add_agent(self, agent: GridAgent) -> None:
        if not isinstance(agent, GridAgent):
            raise TypeError(f"agent must be a {GridAgent.__name__}")
        agent.grid = self
        self._place(agent, agent.x, agent.y)

    def _place(self, agent: GridAgent, x: int, y: int) -> None:
        x, y = self._bound_check(x, y)
        key = (agent.category, agent.id)
        if key in self._registry:
            raise ValueError(f"Agent id {agent.id} already exists on grid!")
        idx = self._to_index(x, y)
        spot = self._spots[idx]
        if not spot._occupants:
            self._mark_occupied(idx)
        spot._occupants.append(agent)
        self._registry[key] = agent
        self._categories.add(agent.category)
        agent.x, agent.y = x, y

    def _unplace(self, agent: GridAgent) -> None:
        key = (agent.category, agent.id)
        if key not in self._registry:
            raise ValueError(f"Agent id {agent.id} does not exist on grid!")
        idx = self._to_index(agent.x, agent.y)
        spot = self._spots[idx]
        spot._occupants.remove(agent)
        del self._registry[key]
        if not spot._occupants:
            self._mark_empty(idx)

    def remove_agent(self, agent: GridAgent) -> None:
        self._unplace(agent)

    def move_agent(self, agent: GridAgent, target_x, target_y) -> None:
        self._unplace(agent)
        self._place(agent, target_x, target_y)

    def get_agent_pos(self, agent_id: int, category) -> Tuple[int, int]:
        agent = self._registry[(category, agent_id)]
        return agent.x, agent.y

    # ── locations / movement ──────────────────────────────────────────────────

    def setup_agent_locations(self, category, initial_placement: str = "direct") -> None:
        self._add_agent_container(category, initial_placement.lower())

    def _add_agent_container(self, container, initial_placement) -> None:
        assert container is not None, "Agent container was None"
        category_id = container[0].category
        assert category_id not in self._agent_containers, f"Category {category_id} already existed!"
        self._agent_containers[category_id] = container
        assert initial_placement in ("random_single", "direct"), \
            f"Invalid initial placement {initial_placement!r}"
        if initial_placement == "random_single":
            for agent in container:
                pos = self.find_empty_spot()
                if pos is None:
                    raise RuntimeError("No empty cell left for random_single placement")
                agent.x, agent.y = pos
                self.add_agent(agent)
        else:  # direct
            for agent in container:
                self.add_agent(agent)

    def rand_move_agent(self, agent: GridAgent, category, range_x, range_y):
        source_x, source_y = agent.x, agent.y
        self._unplace(agent)
        target_x = source_x + self._rng.randint(-range_x, range_x)
        target_y = source_y + self._rng.randint(-range_y, range_y)
        self._place(agent, target_x, target_y)
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
        return set(self._categories)

    # ── neighbour query (returns live agent objects) ──────────────────────────

    def get_neighbors(self, agent, radius=1, moore=True, except_self=True,
                      agent_list: Any = None, return_agents: bool = True):
        """Agents on the cells neighbouring *agent*.

        Returns live ``GridAgent`` objects (cells own them directly, so no
        id-to-object lookup is needed). ``return_agents=False`` yields the raw
        ``(category, id)`` tuples instead, for callers that want that shape.
        ``agent_list`` is accepted for backward compatibility and ignored.
        """
        result = []
        for (px, py) in self._get_neighbor_positions(agent.x, agent.y, radius, moore, except_self):
            result.extend(self._spots[self._to_index(px, py)]._occupants)
        if return_agents:
            return result
        return [(a.category, a.id) for a in result]


__all__ = ["Grid", "Spot"]
