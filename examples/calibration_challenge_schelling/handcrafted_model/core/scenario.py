from abm_auto.runtime import Scenario


class SchellingScenario(Scenario):
    def setup(self):
        # Structural (fixed)
        self.periods = 100
        self.grid_width = 20
        self.grid_height = 20
        # Density: place this fraction of cells as agents; leave the rest empty
        self.density = 0.90
        # Minority group: fraction of agents assigned to group 1 (vs group 0)
        self.fraction_minority = 0.50
        # agent_num is computed: density × width × height
        self.agent_num = int(round(self.density * self.grid_width * self.grid_height))
        self.seed = 0

        # Tunable (calibration target) — CSV-overridden
        self.tolerance = 0.30   # required fraction of same-group neighbours to be happy
