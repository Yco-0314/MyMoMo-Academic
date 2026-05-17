from abm_auto.runtime import Model
from .agent import TemplateGridAgent
from .environment import TemplateEnvironment
from .data_collector import TemplateDataCollector


class TemplateGridModel(Model):
    def create(self):
        self.agents = self.create_agent_list(TemplateGridAgent)
        self.environment = self.create_environment(TemplateEnvironment)
        self.data_collector = self.create_data_collector(TemplateDataCollector)
        self.grid = self.create_grid()  # NO arguments

    def setup(self):
        # 1. Configure grid dimensions from scenario
        self.grid.setup_params(
            width=self.scenario.grid_width,
            height=self.scenario.grid_height,
            wrap=True,
            multi=False,
        )
        # 2. Create agents
        self.agents.setup_agents(agents_num=self.scenario.agent_num)
        # 3. Place agents randomly on grid (one per cell)
        self.grid.setup_agent_locations(
            self.agents, initial_placement="random_single"
        )

    def run(self):
        for t in self.iterator(self.scenario.periods):  # MUST use iterator()
            for agent in self.agents:
                # get_neighbors returns Agent objects — no agent_list needed
                neighbors = self.grid.get_neighbors(agent)
                agent.step()
            self.data_collector.collect(t)
        self.data_collector.save()
