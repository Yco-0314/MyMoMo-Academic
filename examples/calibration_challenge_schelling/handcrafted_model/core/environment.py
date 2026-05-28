import random

from abm_auto.runtime import Environment


def fraction_same_group(agent, grid) -> float:
    """Of agent's grid neighbours, what fraction share its group? Returns 1.0 for isolated."""
    neighbours = grid.get_neighbors(agent)
    if not neighbours:
        return 1.0
    same = sum(1 for n in neighbours if n.group == agent.group)
    return same / len(neighbours)


def is_unhappy(agent, grid, tolerance: float) -> bool:
    return fraction_same_group(agent, grid) < tolerance


class SchellingEnvironment(Environment):
    def setup(self):
        pass

    def step(self, agents, grid, scenario):
        """One Schelling tick: each unhappy agent moves to a random empty spot."""
        tolerance = float(scenario.tolerance)
        unhappy = [a for a in agents if is_unhappy(a, grid, tolerance)]
        if not unhappy:
            return
        random.shuffle(unhappy)
        for agent in unhappy:
            spots = grid.get_empty_spots()
            if not spots:
                break
            x, y = random.choice(spots)
            grid.move_agent(agent, x, y)
