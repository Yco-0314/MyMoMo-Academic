"""ABM Auto Runtime — RuleTable, a library reference-data operator.

Harvested from the Yaman reproduction (ADR-013 Path 2, W3): the hand-written
model loaded a 184-row recipe tree from an external CSV (`task.py`). That is
the canonical shape of a problem the codegen DESIGN phase cannot solve — the
table's contents are not in the paper text, so the design used to spend
several `AI-ASSUMPTION` tags inventing the encoding (item IDs, base items,
which combinations are valid). The structure lives in a DATA FILE, not a
formula.

The fix is the reference-asset channel: a model DECLARES an external rule
table (a `ReferenceAsset` in the spec; the pipeline copies the file into the
generated model's data dir) and loads it with this operator — it never
enumerates or assumes the rows. Generalises beyond Yaman to the many ABMs
driven by an external rule / recipe / transition / payoff table:
crafting & tech trees, chemical reaction networks, state-transition tables,
input-output matrices.

Library vs strategy (same split as FeedforwardLearner / MoranProcess): the
parsing, densification of sparse IDs into a contiguous index space, the
combination lookup, and dependency-level computation are LIBRARY. How an
agent USES the table (which combination to try) is model strategy.
"""
from __future__ import annotations

import csv
import functools
from typing import Any, Optional


def _norm(value: Any) -> Any:
    """Normalise a cell to int when it is an integer-like string, else the
    stripped string. Keeps numeric item IDs sorting numerically (Yaml/Yaman
    use 1..320) while still accepting string-keyed tables."""
    s = str(value).strip()
    try:
        return int(s)
    except (ValueError, TypeError):
        return s


class RuleTable:
    """An external structured rule table loaded into typed lookups.

    Each row declares one OUTPUT item produced by a combination of INPUT items
    (order-free; empty slots ignored), optionally flagged as ``given``
    (available at the start) and carrying a ``weight`` (score/payoff) and a
    ``label``. Item identifiers are densified into a contiguous index space
    ``[0, n_items)`` — the shared vocabulary other operators (e.g.
    FeedforwardLearner) index into.
    """

    def __init__(self, *, id2idx, idx2id, combos, recipe, given, weight, label):
        self._id2idx = id2idx
        self._idx2id = idx2id
        self._combos = combos       # frozenset(input idx) -> output idx
        self._recipe = recipe       # output idx -> frozenset(input idx)
        self._given = tuple(given)   # indices available at the start
        self._weight = weight       # list, per index
        self._label = label         # list, per index

    # ── construction ─────────────────────────────────────────────────────────

    @classmethod
    def from_rows(
        cls,
        rows: list,
        *,
        input_cols: list,
        output_col: str,
        given_col: Optional[str] = None,
        weight_col: Optional[str] = None,
        label_col: Optional[str] = None,
        empty_value: str = "0",
    ) -> "RuleTable":
        if not rows:
            raise ValueError("RuleTable: no rows")
        empty = _norm(empty_value)
        out_ids = [_norm(r[output_col]) for r in rows]
        if len(out_ids) != len(set(out_ids)):
            raise ValueError(
                f"RuleTable: output column {output_col!r} has duplicate ids "
                f"(one rule per output assumed)"
            )
        item_ids = sorted(set(out_ids), key=lambda v: (isinstance(v, str), v))
        id2idx = {iid: i for i, iid in enumerate(item_ids)}
        idx2id = {i: iid for iid, i in id2idx.items()}
        n = len(item_ids)

        given: list = []
        combos: dict = {}
        recipe: dict = {}
        weight = [0.0] * n
        label = [""] * n

        for r in rows:
            out = id2idx[_norm(r[output_col])]
            if weight_col:
                try:
                    weight[out] = float(r[weight_col])
                except (ValueError, TypeError):
                    weight[out] = 0.0
            if label_col:
                label[out] = str(r.get(label_col, "") or "")
            if given_col and str(r.get(given_col, "")).strip() in ("1", "true", "True", "yes"):
                given.append(out)
                continue
            ings = frozenset(
                id2idx[_norm(r[c])] for c in input_cols if _norm(r[c]) != empty
            )
            if not ings:
                # a non-given row with no inputs: treat as a base item too
                given.append(out)
                continue
            combos[ings] = out
            recipe[out] = ings

        return cls(id2idx=id2idx, idx2id=idx2id, combos=combos, recipe=recipe,
                   given=given, weight=weight, label=label)

    @classmethod
    def from_csv(cls, path: str, **kwargs) -> "RuleTable":
        with open(path, newline="") as fh:
            rows = list(csv.DictReader(fh))
        return cls.from_rows(rows, **kwargs)

    # ── lookups ──────────────────────────────────────────────────────────────

    @property
    def n_items(self) -> int:
        return len(self._id2idx)

    def index_of(self, item_id: Any) -> int:
        return self._id2idx[_norm(item_id)]

    def id_of(self, idx: int) -> Any:
        return self._idx2id[idx]

    def combine(self, inputs) -> "int | None":
        """Output index for an exact set of input indices, or None if the
        combination is not a valid rule. Order/duplicates ignored."""
        return self._combos.get(frozenset(inputs))

    def recipe_for(self, output_idx: int) -> "frozenset | None":
        return self._recipe.get(output_idx)

    def given_indices(self) -> tuple:
        return self._given

    def weight_of(self, idx: int) -> float:
        return self._weight[idx]

    def label_of(self, idx: int) -> str:
        return self._label[idx]

    # ── derived structure ──────────────────────────────────────────────────

    @functools.lru_cache(maxsize=None)
    def level_of(self, idx: int) -> int:
        """Longest dependency depth from a given item (given items = 0)."""
        if idx in self._given:
            return 0
        rec = self._recipe.get(idx)
        if not rec:
            return 0
        return 1 + max(self.level_of(s) for s in rec)

    def level_counts(self) -> list:
        if self.n_items == 0:
            return []
        levels = [self.level_of(i) for i in range(self.n_items)]
        counts = [0] * (max(levels) + 1)
        for lv in levels:
            counts[lv] += 1
        return counts


def self_test() -> bool:
    """Library self-test (ADR-013 Gate philosophy): on a synthetic rule table,
    parsing + densification + combination lookup + dependency levels must be
    correct. Checked once so generated code trusting the library is safe.

    Table: bases {1,2,3}; 1+2 -> 4; 4+3 -> 5. Sparse ids (skip 6..9) to test
    densification. Expect 5 items, level_counts [3,1,1], correct combine().
    """
    rows = [
        {"a": "0", "b": "0", "out": "1", "given": "1", "w": "0", "name": "wood"},
        {"a": "0", "b": "0", "out": "2", "given": "1", "w": "0", "name": "stone"},
        {"a": "0", "b": "0", "out": "3", "given": "1", "w": "0", "name": "water"},
        {"a": "1", "b": "2", "out": "12", "given": "0", "w": "5", "name": "axe"},
        {"a": "12", "b": "3", "out": "20", "given": "0", "w": "9", "name": "totem"},
    ]
    t = RuleTable.from_rows(rows, input_cols=["a", "b"], output_col="out",
                            given_col="given", weight_col="w", label_col="name")
    if t.n_items != 5:
        return False
    if t.combine([t.index_of(1), t.index_of(2)]) != t.index_of(12):
        return False
    if t.combine([t.index_of(12), t.index_of(3)]) != t.index_of(20):
        return False
    if t.combine([t.index_of(1), t.index_of(3)]) is not None:   # not a valid rule
        return False
    if set(t.given_indices()) != {t.index_of(1), t.index_of(2), t.index_of(3)}:
        return False
    if t.weight_of(t.index_of(20)) != 9.0 or t.label_of(t.index_of(20)) != "totem":
        return False
    return t.level_counts() == [3, 1, 1]
