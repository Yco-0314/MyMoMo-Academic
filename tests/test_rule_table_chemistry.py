"""Second adapter for RuleTable — cross-domain, "two adapters = real seam".

The first RuleTable adapter is the Yaman recipe tree (cultural innovation). This
is a deliberately different DOMAIN: an artificial-chemistry reactor (the kind
of ABM in Fontana's AlChemy / autocatalytic-set research). Molecules are
agents in a well-mixed soup; each collision of two molecules looks up a
reaction in the RuleTable; reactive collisions produce a new molecule. Starting
from base elements, the cascade of bimolecular reactions must synthesise a
deep target molecule — emergent chemical complexity driven entirely by the
same RuleTable operator.

Different from Yaman: a chemistry domain, 2-reactant rules (Yaman used 3),
collision dynamics (not strategy-driven choice), `weight_of` read as reaction
energy. Same operator. If it works here too, RuleTable is a real seam.
"""
from __future__ import annotations

import random

from abm_auto.runtime import RuleTable


def _reaction_network() -> RuleTable:
    # base elements H(1) O(2) C(3); a bimolecular reaction cascade up to a
    # level-3 product (carbonic acid). r1,r2 = reactant ids; mol = product.
    rows = [
        {"r1": "0", "r2": "0", "mol": "1", "base": "1", "energy": "0", "name": "H"},
        {"r1": "0", "r2": "0", "mol": "2", "base": "1", "energy": "0", "name": "O"},
        {"r1": "0", "r2": "0", "mol": "3", "base": "1", "energy": "0", "name": "C"},
        {"r1": "1", "r2": "2", "mol": "10", "base": "0", "energy": "2", "name": "OH"},
        {"r1": "10", "r2": "1", "mol": "11", "base": "0", "energy": "4", "name": "H2O"},
        {"r1": "3", "r2": "2", "mol": "12", "base": "0", "energy": "3", "name": "CO"},
        {"r1": "12", "r2": "2", "mol": "13", "base": "0", "energy": "5", "name": "CO2"},
        {"r1": "11", "r2": "13", "mol": "14", "base": "0", "energy": "9", "name": "H2CO3"},
    ]
    return RuleTable.from_rows(rows, input_cols=["r1", "r2"], output_col="mol",
                              given_col="base", weight_col="energy", label_col="name")


def _run_reactor(seed: int, steps: int):
    """Well-mixed reactor: random pairwise collisions; a reactive pair appends
    its product (autocatalytic growth — reactants persist). Returns (table,
    final soup multiset)."""
    t = _reaction_network()
    rng = random.Random(seed)
    soup = list(t.given_indices()) * 20          # 20 each of H, O, C
    for _ in range(steps):
        i, j = rng.sample(range(len(soup)), 2)
        product = t.combine([soup[i], soup[j]])
        if product is not None:
            soup.append(product)
    return t, soup


def test_rule_table_drives_emergent_chemistry() -> None:
    """From base elements, the SAME operator's reaction lookups synthesise the
    deep target molecule (H2CO3, reaction-level 3) via the collision cascade."""
    t, soup = _run_reactor(seed=0, steps=3000)
    present = set(soup)
    target = t.index_of(14)                       # H2CO3
    assert target in present, "deep target molecule was never synthesised"
    assert max(t.level_of(m) for m in present) == 3
    # the intermediate cascade must all be present too (real reachability)
    for mol_id in (10, 11, 12, 13):
        assert t.index_of(mol_id) in present, f"intermediate {mol_id} missing"


def test_reaction_lookup_is_order_free_and_correct() -> None:
    t = _reaction_network()
    # combine is a set lookup: order of reactants must not matter
    assert t.combine([t.index_of(1), t.index_of(2)]) == t.index_of(10)   # H+O
    assert t.combine([t.index_of(2), t.index_of(1)]) == t.index_of(10)   # O+H (same)
    assert t.label_of(t.index_of(14)) == "H2CO3"
    assert t.weight_of(t.index_of(14)) == 9.0                            # reaction energy
    assert t.combine([t.index_of(1), t.index_of(3)]) is None             # H+C: no reaction


def test_no_reaction_means_inert_soup() -> None:
    """A soup of only non-reacting base pairs grows by nothing (operator does
    not invent reactions)."""
    t = _reaction_network()
    rng = random.Random(1)
    soup = [t.index_of(1), t.index_of(3)] * 10    # only H and C — no H+C reaction
    start = len(soup)
    for _ in range(500):
        i, j = rng.sample(range(len(soup)), 2)
        product = t.combine([soup[i], soup[j]])
        if product is not None:
            soup.append(product)
    assert len(soup) == start                     # nothing synthesised
