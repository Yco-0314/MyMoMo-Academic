"""YamanModel — assembles the population, runs the CCE loop, records metrics.

No grid, no network: a well-mixed population under a Moran process. Each
agent carries its own FeedforwardLearner (the W2 learned operator) as its
semantic model M.

The primary dependent variable (the paper's headline) is the cultural
repertoire size: the number of DISTINCT non-base items the population has
collectively discovered, recorded once per generation.
"""
from __future__ import annotations

import os
import random

from abm_auto.runtime import FeedforwardLearner, Model, MoranProcess, RuleTable

from .agent import Innovator
from .data_collector import YamanDataCollector
from .environment import YamanEnvironment


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

        # The harvested operators (ADR-013): the recipe tree is the W3
        # RuleTable, the turnover the W4 MoranProcess — the same operators the
        # codegen pipeline now provides, exercised in a real running model.
        rules_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "reference_data", "rules_tidied.csv"
        )
        self._task = RuleTable.from_csv(
            rules_path, input_cols=["c1", "c2", "c3"], output_col="item",
            given_col="given", weight_col="point", label_col="name_simplified",
        )
        self._moran = MoranProcess(fitness_attr="score", death_model="gompertz",
                                   age_attr="age")
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
        base = set(self._task.given_indices())
        discovered = set()
        for a in self.agents:
            discovered |= a.inventory
        discovered -= base

        env = self.environment
        env.repertoire_size = len(discovered)
        env.max_level = max((self._task.level_of(i) for i in discovered), default=0)
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
            self.environment.step(self.agents, self.scenario, self._task, self._moran, self._rng)
        # capture the end state after the final generation
        self._refresh_metrics()
        self.data_collector.collect(periods)
        self.data_collector.save()
