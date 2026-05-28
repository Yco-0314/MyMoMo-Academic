from abm_auto.runtime import Scenario


class VirusScenario(Scenario):
    def setup(self):
        # Structural (fixed)
        self.periods = 250
        self.agent_num = 150
        self.average_degree = 6
        self.initial_outbreak_size = 3
        self.virus_check_frequency = 1
        self.seed = 0

        # Tunable (calibration targets) — values get overridden by CSV.
        # Defaults use the inferred GT (see benchmark_calibration_challenge
        # docstring re: PDF typo — printed 0.3, actual ≈ 2.5).
        self.virus_spread_chance = 4.4          # percent per neighbour per tick
        self.recovery_chance = 2.5              # percent per infected per check
        self.gain_resistance_chance = 25.0      # percent at recovery
