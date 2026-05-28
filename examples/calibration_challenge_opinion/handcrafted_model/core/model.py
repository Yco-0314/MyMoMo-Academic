import random
import statistics

from abm_auto.runtime import Model, topologies

from .agent import Citizen
from .data_collector import OpinionDataCollector
from .environment import OpinionEnvironment, opinion_clusters


class OpinionModel(Model):
    def create(self):
        self.agents = self.create_agent_list(Citizen)
        self.environment = self.create_environment(OpinionEnvironment)
        self.data_collector = self.create_data_collector(OpinionDataCollector)
        self.network = self.create_network()

    def setup(self):
        random.seed(int(getattr(self.scenario, "seed", 0)))

        # 1. Create agents with uniform random initial opinions
        self.agents.setup_agents(agents_num=self.scenario.agent_num)
        for a in self.agents:
            a.opinion = random.random()

        # 2. Build network — Watts-Strogatz small-world (different topology
        #    from SIR's spatially-clustered, exercises a different adapter)
        self.network.setup_agent_connections(
            agent_lists=[self.agents],
            topology=topologies.watts_strogatz(
                k=int(self.scenario.average_degree),
                p=0.10,
            ),
        )

        # 3. Seed metrics
        self._refresh_metrics()

    def _refresh_metrics(self):
        ops = [a.opinion for a in self.agents]
        self.environment.mean_opinion = statistics.mean(ops) if ops else 0.0
        self.environment.opinion_variance = statistics.pvariance(ops) if ops else 0.0
        self.environment.n_clusters = opinion_clusters(self.agents)

    def run(self):
        for t in self.iterator(self.scenario.periods):
            self._refresh_metrics()
            self.data_collector.collect(t)
            self.environment.step(self.agents, self.network, self.scenario)
        self.data_collector.save()
