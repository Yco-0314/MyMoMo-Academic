import random
import statistics

from abm_auto.runtime import Model

from .agent import Resident
from .data_collector import SchellingDataCollector
from .environment import SchellingEnvironment, fraction_same_group, is_unhappy


class SchellingModel(Model):
    def create(self):
        self.agents = self.create_agent_list(Resident)
        self.environment = self.create_environment(SchellingEnvironment)
        self.data_collector = self.create_data_collector(SchellingDataCollector)
        self.grid = self.create_grid()

    def setup(self):
        random.seed(int(getattr(self.scenario, "seed", 0)))

        # 1. Grid dimensions
        self.grid.setup_params(
            width=int(self.scenario.grid_width),
            height=int(self.scenario.grid_height),
        )

        # 2. Create agents (count = density × grid cells, computed in Scenario)
        self.agents.setup_agents(agents_num=int(self.scenario.agent_num))

        # 3. Assign groups randomly (with fraction_minority going to group 1)
        n_minority = int(round(self.scenario.fraction_minority * len(self.agents)))
        group_assignments = [1] * n_minority + [0] * (len(self.agents) - n_minority)
        random.shuffle(group_assignments)
        for a, g in zip(self.agents, group_assignments):
            a.group = g

        # 4. Place on grid randomly
        self.grid.setup_agent_locations(self.agents, initial_placement="random_single")

        # 5. Initial metrics
        self._refresh_metrics()

    def _refresh_metrics(self):
        tol = float(self.scenario.tolerance)
        fractions = [fraction_same_group(a, self.grid) for a in self.agents]
        self.environment.segregation_index = statistics.mean(fractions) if fractions else 0.0
        self.environment.n_unhappy = sum(1 for f in fractions if f < tol)
        self.environment.fraction_segregated = (
            sum(1 for f in fractions if f >= 0.75) / len(fractions) if fractions else 0.0
        )

    def run(self):
        for t in self.iterator(self.scenario.periods):
            self._refresh_metrics()
            self.data_collector.collect(t)
            self.environment.step(self.agents, self.grid, self.scenario)
        self.data_collector.save()
