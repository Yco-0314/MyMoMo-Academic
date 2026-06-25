"""Reusable GIS mechanisms over a neighbor callable.

Mechanisms in this module know about integer agent ids and neighbors only.
GIS spaces adapt into this interface elsewhere.
"""
from __future__ import annotations

import random
from numbers import Integral, Real
from typing import Callable, Iterable

NeighborsOf = Callable[[int], Iterable[int]]


def _initial_adopted(n_agents: int, seeds: Iterable[int]) -> list[bool]:
    if isinstance(n_agents, bool) or not isinstance(n_agents, Integral) or n_agents < 0:
        raise ValueError("n_agents must be a non-negative integer")
    adopted = [False] * int(n_agents)
    for seed in seeds:
        if isinstance(seed, bool) or not isinstance(seed, Integral):
            raise ValueError("seed ids must be integers")
        if not 0 <= int(seed) < int(n_agents):
            raise ValueError(f"seed id must be in [0, {n_agents})")
        adopted[int(seed)] = True
    return adopted


def _valid_adopted_neighbors(i: int, neighbors_of: NeighborsOf, adopted: list[bool]) -> int:
    n_agents = len(adopted)
    return sum(
        1
        for j in neighbors_of(i)
        if isinstance(j, Integral)
        and not isinstance(j, bool)
        and 0 <= int(j) < n_agents
        and adopted[int(j)]
    )


def run_contagion(
    n_agents: int,
    neighbors_of: NeighborsOf,
    beta: float = 0.2,
    steps: int = 20,
    seed: int = 0,
    seeds: Iterable[int] = (0,),
) -> dict:
    if isinstance(beta, bool) or not isinstance(beta, Real) or not 0 <= beta <= 1:
        raise ValueError("beta must be a probability in [0, 1]")
    rng = random.Random(seed)
    adopted = _initial_adopted(n_agents, seeds)
    history = [sum(adopted)]

    for _ in range(int(steps)):
        nxt = adopted[:]
        for i in range(int(n_agents)):
            if not adopted[i]:
                k = _valid_adopted_neighbors(i, neighbors_of, adopted)
                if k and rng.random() < 1.0 - (1.0 - beta) ** k:
                    nxt[i] = True
        adopted = nxt
        history.append(sum(adopted))

    return {"history": history, "final": sum(adopted), "n_agents": int(n_agents)}


def run_threshold_adoption(
    n_agents: int,
    neighbors_of: NeighborsOf,
    threshold: int = 1,
    steps: int = 20,
    seeds: Iterable[int] = (0,),
) -> dict:
    if isinstance(threshold, bool) or not isinstance(threshold, Integral) or threshold <= 0:
        raise ValueError("threshold must be a positive integer")
    adopted = _initial_adopted(n_agents, seeds)
    history = [sum(adopted)]

    for _ in range(int(steps)):
        nxt = adopted[:]
        for i in range(int(n_agents)):
            if not adopted[i] and _valid_adopted_neighbors(i, neighbors_of, adopted) >= int(threshold):
                nxt[i] = True
        adopted = nxt
        history.append(sum(adopted))

    return {
        "history": history,
        "final": sum(adopted),
        "n_agents": int(n_agents),
        "adopted": adopted,
    }


def _default_chain_neighbors(n_agents: int) -> NeighborsOf:
    def neighbors_of(i: int) -> list[int]:
        out = []
        if i > 0:
            out.append(i - 1)
        if i < n_agents - 1:
            out.append(i + 1)
        return out

    return neighbors_of


def _empty_neighbors(_: int) -> tuple:
    return ()


def mechanism_space_gate(
    connected_neighbors_of: NeighborsOf | None = None,
    isolated_neighbors_of: NeighborsOf | None = None,
    n_agents: int = 8,
    threshold: int = 1,
    steps: int = 7,
    seeds: Iterable[int] = (0,),
):
    seed_ids = tuple(seeds)
    initial = sum(_initial_adopted(n_agents, seed_ids))
    connected_neighbors_of = connected_neighbors_of or _default_chain_neighbors(n_agents)
    isolated_neighbors_of = isolated_neighbors_of or _empty_neighbors

    connected = run_threshold_adoption(
        n_agents,
        connected_neighbors_of,
        threshold=threshold,
        steps=steps,
        seeds=seed_ids,
    )
    isolated = run_threshold_adoption(
        n_agents,
        isolated_neighbors_of,
        threshold=threshold,
        steps=steps,
        seeds=seed_ids,
    )

    if connected["final"] <= initial:
        return False, (
            "no connected-neighbor spread; "
            f"connected final={connected['final']} initial={initial}"
        )
    if isolated["final"] != initial:
        return False, (
            "isolated neighbors changed adoption; "
            f"isolated final={isolated['final']} initial={initial}"
        )
    if connected["final"] <= isolated["final"]:
        return False, (
            "neighbor seam did not change outcome; "
            f"connected={connected['final']} isolated={isolated['final']}"
        )
    return (
        True,
        "neighbor seam controls threshold adoption "
        f"(connected {connected['final']} vs isolated {isolated['final']})",
    )


def mechanism_contagion_gate(
    connected_neighbors_of: NeighborsOf | None = None,
    isolated_neighbors_of: NeighborsOf | None = None,
    n_agents: int = 8,
    beta: float = 1.0,
    steps: int = 7,
    seed: int = 0,
    seeds: Iterable[int] = (0,),
):
    seed_ids = tuple(seeds)
    initial = sum(_initial_adopted(n_agents, seed_ids))
    connected_neighbors_of = connected_neighbors_of or _default_chain_neighbors(n_agents)
    isolated_neighbors_of = isolated_neighbors_of or _empty_neighbors

    connected = run_contagion(
        n_agents,
        connected_neighbors_of,
        beta=beta,
        steps=steps,
        seed=seed,
        seeds=seed_ids,
    )
    isolated = run_contagion(
        n_agents,
        isolated_neighbors_of,
        beta=beta,
        steps=steps,
        seed=seed,
        seeds=seed_ids,
    )

    if connected["final"] <= initial:
        return False, (
            "no connected-neighbor contagion spread; "
            f"connected final={connected['final']} initial={initial}"
        )
    if isolated["final"] != initial:
        return False, (
            "isolated neighbors changed contagion; "
            f"isolated final={isolated['final']} initial={initial}"
        )
    if connected["final"] <= isolated["final"]:
        return False, (
            "neighbor seam did not change contagion outcome; "
            f"connected={connected['final']} isolated={isolated['final']}"
        )
    return (
        True,
        "neighbor seam controls contagion "
        f"(connected {connected['final']} vs isolated {isolated['final']}); "
        "not spatial validation",
    )
