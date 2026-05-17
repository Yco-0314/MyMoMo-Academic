from abm_auto.runtime import Model
from .agent import TemplateAgent
from .environment import TemplateEnvironment
from .data_collector import TemplateDataCollector

class TemplateModel(Model):
    def create(self):
        self.agent_list = self.create_agent_list(TemplateAgent)
        self.environment = self.create_environment(TemplateEnvironment)
        self.data_collector = self.create_data_collector(TemplateDataCollector)

    def setup(self):
        self.agent_list.setup_agents(agents_num=self.scenario.agent_num)

    def run(self):
        for t in self.iterator(self.scenario.periods):  # MUST use iterator(), not range()
            self.environment.step()
            self.data_collector.collect(t)
        self.data_collector.save()
