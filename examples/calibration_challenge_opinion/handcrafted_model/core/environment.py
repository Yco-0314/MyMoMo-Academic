import random
import statistics

from abm_auto.runtime import Environment


class OpinionEnvironment(Environment):
    def setup(self):
        pass

    def step(self, agents, network, scenario):
        """Deffuant pairwise interaction (one round per agent per tick).

        For each agent, pick one random neighbor. If |Δopinion| < μ, both
        move toward each other by fraction α. Otherwise no change.
        """
        mu = float(scenario.confidence_threshold)
        alpha = float(scenario.convergence_rate)

        for a in agents:
            neighbors = network.get_neighbors(a)
            if not neighbors:
                continue
            b = random.choice(neighbors)
            diff = b.opinion - a.opinion
            if abs(diff) < mu:
                # Both move toward each other (Deffuant is symmetric)
                a.opinion += alpha * diff
                b.opinion -= alpha * diff


def opinion_clusters(agents, gap: float = 0.10) -> int:
    """Count distinct opinion clusters by sorting + counting big gaps.

    A 'gap' is two adjacent sorted opinions further apart than `gap`.
    With Deffuant convergence, surviving clusters stay > μ apart, so this
    measures consensus-vs-polarization regime.
    """
    if len(agents) == 0:
        return 0
    sorted_ops = sorted(a.opinion for a in agents)
    clusters = 1
    for prev, curr in zip(sorted_ops, sorted_ops[1:]):
        if curr - prev > gap:
            clusters += 1
    return clusters
