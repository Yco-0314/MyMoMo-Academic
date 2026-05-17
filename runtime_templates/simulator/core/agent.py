from abm_auto.runtime import Agent

class TemplateAgent(Agent):
    def setup(self):
        # _safe_attr preserves CSV-loaded values (setup() runs after CSV loading)
        self.state: int = self._safe_attr("state", 0)
        self.some_property: float = 0.0

    def step(self):
        pass
