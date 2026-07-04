from abm_auto.runtime import Model
from .agent import MyMoMoAgent
from .environment import MyMoMoEnvironment
from .data_collector import MyMoMoDataCollector

class MyMoMoModel(Model):
    def create(self):
        self.agent_list = self.create_agent_list(MyMoMoAgent)
        self.environment = self.create_environment(MyMoMoEnvironment)
        self.data_collector = self.create_data_collector(MyMoMoDataCollector)

    def setup(self):
        self.agent_list.setup_agents(agents_num=self.scenario.agent_num)

    def run(self):
        for t in self.iterator(self.scenario.periods):  # MUST use iterator(), not range()
            self.environment.step()
            self.data_collector.collect(t)
        self.data_collector.save()
