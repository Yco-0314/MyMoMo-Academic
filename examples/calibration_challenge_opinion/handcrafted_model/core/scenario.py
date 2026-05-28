from abm_auto.runtime import Scenario


class OpinionScenario(Scenario):
    def setup(self):
        # Structural (fixed)
        self.periods = 200
        self.agent_num = 200
        self.average_degree = 8
        self.seed = 0

        # Tunable (calibration targets) — CSV-overridden
        self.confidence_threshold = 0.20    # μ in Deffuant — interact only if |Δopinion| < μ
        self.convergence_rate = 0.30        # α in Deffuant — pull toward neighbor by this fraction
