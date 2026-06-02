"""The Totem innovation task — loaded from the REAL Yaman et al. recipe tree.

Source of truth: ``reference_data/rules_tidied.csv`` (downloaded from the
paper's OSF repository, osf.io/m642a, `data/empirical/rules_tidied.csv`).
Each row is one item: its recipe (`c1,c2,c3` ingredient IDs, order-free,
0 = empty slot), whether it is `given` at the start, and its `point` score.

This module turns that CSV into the fixed task structure the model needs:

  * a contiguous item index space [0, n_items) — the FeedforwardLearner's
    vocabulary (item IDs in the CSV are sparse, up to 320; we densify).
  * ``recipe_lookup``: frozenset(ingredient indices) -> product index.
  * ``product2recipe``: product index -> frozenset(ingredient indices).
  * ``score[idx]`` and ``level[idx]`` (level = longest dependency depth).

Nothing here is invented: the level distribution this produces is
[6,4,2,2,2,3,3,7,11,48,96], byte-for-byte the paper's Table-1 task
(SI lines 22-23 / 407). The tree is real; only the simulation dynamics
(Algorithms 1 & 2) are hand-written from the SI pseudocode.

HARVEST NOTE (Path-2 → architecture): this loader is the prototype of a
future codegen library operator — a "structured task graph" primitive
(W3 candidate). A research model that references an external recipe/rule
table should DECLARE it (a reference-asset slot) and get this loader, not
re-derive 184 edges as AI-ASSUMPTION tags. That is the thing the
viability gate was rejecting.
"""
from __future__ import annotations

import csv
import functools
import os
from dataclasses import dataclass, field

# rules_tidied.csv lives two levels up from this file, in reference_data/.
_DEFAULT_RULES = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "reference_data", "rules_tidied.csv")
)


@dataclass
class TotemTask:
    """Immutable task structure shared by every agent in a run."""

    n_items: int
    id2idx: dict[int, int]
    idx2id: dict[int, int]
    base_indices: tuple[int, ...]                       # the 6 given items
    recipe_lookup: dict[frozenset, int]                 # ingredients -> product
    product2recipe: dict[int, frozenset]                # product -> ingredients
    score: list[float]                                  # per index
    level: list[int]                                    # per index
    caption: list[str] = field(default_factory=list)

    @property
    def max_level(self) -> int:
        return max(self.level)

    def craft(self, ingredient_indices) -> "int | None":
        """Return the product index for an exact set of ingredients, or None
        if the combination is not a valid recipe. Order/duplicates ignored."""
        return self.recipe_lookup.get(frozenset(ingredient_indices))

    def level_counts(self) -> list[int]:
        counts = [0] * (self.max_level + 1)
        for lv in self.level:
            counts[lv] += 1
        return counts


def load_totem_task(path: "str | None" = None) -> TotemTask:
    path = path or _DEFAULT_RULES
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))

    # Dense, deterministic index space ordered by the CSV's item id.
    item_ids = sorted(int(r["item"]) for r in rows)
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("rules_tidied.csv has duplicate item ids; tree assumed 1 recipe/item")
    id2idx = {iid: i for i, iid in enumerate(item_ids)}
    idx2id = {i: iid for iid, i in id2idx.items()}
    n = len(item_ids)

    base_indices: list[int] = []
    recipe_lookup: dict[frozenset, int] = {}
    product2recipe: dict[int, frozenset] = {}
    score = [0.0] * n
    caption = [""] * n

    for r in rows:
        prod = id2idx[int(r["item"])]
        score[prod] = float(r["point"])
        caption[prod] = r.get("name_simplified", "") or r.get("caption_semantic", "")
        if r["given"] == "1":
            base_indices.append(prod)
            continue
        ings = frozenset(
            id2idx[int(r[c])] for c in ("c1", "c2", "c3") if int(r[c]) != 0
        )
        if not ings:
            raise ValueError(f"non-given item {r['item']} has empty recipe")
        recipe_lookup[ings] = prod
        product2recipe[prod] = ings

    # level = longest path from a base item (base = 0).
    base_set = set(base_indices)

    @functools.lru_cache(maxsize=None)
    def _level(idx: int) -> int:
        if idx in base_set:
            return 0
        rec = product2recipe.get(idx)
        if not rec:
            return 0
        return 1 + max(_level(s) for s in rec)

    level = [_level(i) for i in range(n)]

    return TotemTask(
        n_items=n,
        id2idx=id2idx,
        idx2id=idx2id,
        base_indices=tuple(base_indices),
        recipe_lookup=recipe_lookup,
        product2recipe=product2recipe,
        score=score,
        level=level,
        caption=caption,
    )
