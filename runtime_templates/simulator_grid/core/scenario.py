from abm_auto.runtime import Scenario


class TemplateScenario(Scenario):
    def setup(self):
        self.periods: int = 0
        self.agent_num: int = 0
        self.grid_width: int = 0
        self.grid_height: int = 0
