"""YamanModel — assembles the population, runs the CCE loop, records metrics.

No grid, no network: a well-mixed population under a Moran process. Each
agent carries its own FeedforwardLearner (the W2 learned operator) as its
semantic model M.

The primary dependent variable (the paper's headline) is the cultural
repertoire size: the number of DISTINCT non-base items the population has
collectively discovered, recorded once per generation.
"""
from __future__ import annotations

import random

from abm_auto.runtime import FeedforwardLearner, Model

from .agent import Innovator
from .data_collector import YamanDataCollector
from .environment import YamanEnvironment
from .task import load_totem_task


class YamanModel(Model):
    def create(self):
        self.agents = self.create_agent_list(Innovator)
        self.environment = self.create_environment(YamanEnvironment)
        self.data_collector = self.create_data_collector(YamanDataCollector)

    def setup(self):
        # Replicate runs of one scenario must differ: fold the run index into
        # the seed (the framework reuses scenario.seed across runs otherwise).
        run_id = int(getattr(self, "run_id_in_scenario", 0))
        seed = int(getattr(self.scenario, "seed", 0)) * 100000 + run_id
        self._rng = random.Random(seed)

        self._task = load_totem_task()
        self.agents.setup_agents(agents_num=int(self.scenario.agent_num))

        ed = int(self.scenario.embed_dim)
        hd = int(self.scenario.hidden_dim)
        lr = float(self.scenario.learning_rate)
        for k, agent in enumerate(self.agents):
            learner = FeedforwardLearner(
                n_items=self._task.n_items,
                embed_dim=ed, hidden_dim=hd, learning_rate=lr,
                seed=seed + 1 + k,
            )
            agent.attach(self._task, learner)

        self._refresh_metrics()

    def _refresh_metrics(self):
        base = set(self._task.base_indices)
        discovered = set()
        for a in self.agents:
            discovered |= a.inventory
        discovered -= base

        env = self.environment
        env.repertoire_size = len(discovered)
        env.max_level = max((self._task.level[i] for i in discovered), default=0)
        scores = [a.score for a in self.agents]
        env.mean_score = sum(scores) / len(scores) if scores else 0.0
        env.max_score = max(scores) if scores else 0.0
        env.mean_inventory = (
            sum(len(a.inventory) for a in self.agents) / len(self.agents)
            if self.agents else 0.0
        )

    def run(self):
        periods = int(self.scenario.periods)
        for t in self.iterator(periods):
            self._refresh_metrics()
            self.data_collector.collect(t)
            self.environment.step(self.agents, self.scenario, self._task, self._rng)
        # capture the end state after the final generation
        self._refresh_metrics()
        self.data_collector.collect(periods)
        self.data_collector.save()
