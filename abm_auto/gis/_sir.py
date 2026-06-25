"""Handcrafted SIR on a RasterSpace — the deterministic reference model.

One agent per cell. S/I/R state. Infection pressure on a cell = beta * (sum of
infected neighbours) * local-density weight. Recovery with prob gamma. Seeded
RNG -> reproducible. No LLM, no codegen — this is the gateable reference."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List

import numpy as np

S, I, R = 0, 1, 2


@dataclass
class SirResult:
    infected_history: List[int] = field(default_factory=list)
    final_infected_field: np.ndarray = None  # cells ever-infected (I or R)


def run_raster_sir(space, seed=0, steps=50, beta=0.4, gamma=0.05) -> SirResult:
    rng = random.Random(seed)
    rows, cols = space.field.data.shape
    dens = space.field.data
    dmax = float(dens.max()) or 1.0
    state = np.full((rows, cols), S, dtype=int)

    # seed one infection at the densest cell
    r0, c0 = np.unravel_index(int(np.argmax(dens)), dens.shape)
    state[r0, c0] = I

    history: List[int] = [int((state == I).sum())]
    ever = (state == I)

    for _ in range(steps):
        nxt = state.copy()
        for r in range(rows):
            for c in range(cols):
                if state[r, c] == S:
                    inf_nb = sum(
                        1 for (nc, nr) in space.neighbor_cells(c, r)
                        if state[nr, nc] == I
                    )
                    if inf_nb:
                        p = 1.0 - (1.0 - beta * (dens[r, c] / dmax)) ** inf_nb
                        if rng.random() < p:
                            nxt[r, c] = I
                elif state[r, c] == I:
                    if rng.random() < gamma:
                        nxt[r, c] = R
        state = nxt
        ever = ever | (state == I)
        history.append(int((state == I).sum()))

    return SirResult(infected_history=history,
                     final_infected_field=ever.astype(float))
