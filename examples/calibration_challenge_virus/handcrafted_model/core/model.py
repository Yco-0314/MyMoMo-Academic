import random

from abm_auto.runtime import Model

from .agent import Person
from .data_collector import VirusDataCollector
from .environment import VirusEnvironment


class VirusModel(Model):
    def create(self):
        self.agents = self.create_agent_list(Person)
        self.environment = self.create_environment(VirusEnvironment)
        self.data_collector = self.create_data_collector(VirusDataCollector)
        self.network = self.create_network()

    def setup(self):
        # Reproducibility — match the source-paper `random-seed 0`
        random.seed(int(getattr(self.scenario, "seed", 0)))

        # 1. Create agents
        self.agents.setup_agents(agents_num=self.scenario.agent_num)

        # 2. Initial outbreak: pick K agents to be infected
        initial = int(self.scenario.initial_outbreak_size)
        infected_idx = set(random.sample(range(len(self.agents)), initial))
        for i, a in enumerate(self.agents):
            a.state = 1 if i in infected_idx else 0
            a.virus_check_timer = 0

        # 3. Build network. Watts-Strogatz: k ≈ average_degree (must be even),
        #    rewiring prob 0.1. Aligns with the source-paper "spatially clustered network"
        #    which is a small-world variant.
        k = int(self.scenario.average_degree)
        if k % 2 == 1:
            k += 1
        self.network.setup_agent_connections(
            agent_lists=[self.agents],
            network_type="watts_strogatz_graph",
            network_params={"k": k, "p": 0.1},
        )

        # 4. Init aggregate counters on environment for DataCollector
        self._refresh_counts()

    def _refresh_counts(self):
        self.environment.count_s = sum(1 for a in self.agents if a.state == 0)
        self.environment.count_i = sum(1 for a in self.agents if a.state == 1)
        self.environment.count_r = sum(1 for a in self.agents if a.state == 2)

    def run(self):
        # Collect tick 0 BEFORE any step, so output aligns with the challenge's expected format
        # (observed.csv row 0 is the initial state).
        for t in self.iterator(self.scenario.periods):
            self._refresh_counts()
            self.data_collector.collect(t)
            # Step (next iteration's counts reflect this step's outcome)
            self.environment.step(self.agents, self.network, self.scenario)
        self.data_collector.save()
