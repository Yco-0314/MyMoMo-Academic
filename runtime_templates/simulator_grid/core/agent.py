import random
from abm_auto.runtime import GridAgent


class TemplateGridAgent(GridAgent):
    # set_category() defaults to category=0 — override only for multi-type grids

    def setup(self):
        # _safe_attr preserves CSV-loaded values (setup() runs after CSV loading)
        self.state: int = self._safe_attr("state", 0)

    def step(self):
        pass
