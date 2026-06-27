from abm_auto.runtime import Scenario

class MyMoMoScenario(Scenario):
    def setup(self):
        self.periods = 0
        self.agent_num = 0
