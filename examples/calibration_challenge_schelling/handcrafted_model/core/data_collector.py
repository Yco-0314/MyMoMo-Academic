from abm_auto.runtime import DataCollector


class SchellingDataCollector(DataCollector):
    def setup(self):
        # Per-tick environment-level metrics. All Schelling-specific names —
        # distinct from SIR and Opinion, exercises COLUMN_ALIASES generality.
        self.add_environment_property("n_unhappy")
        self.add_environment_property("segregation_index")
        self.add_environment_property("fraction_segregated")
