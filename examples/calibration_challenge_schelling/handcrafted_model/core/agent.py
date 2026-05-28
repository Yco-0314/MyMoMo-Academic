from abm_auto.runtime import GridAgent


class Resident(GridAgent):
    def setup(self):
        # group: 0 or 1 (two-group Schelling)
        self.group: int = self._safe_attr("group", 0)
