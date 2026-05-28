from abm_auto.runtime import DataCollector


class OpinionDataCollector(DataCollector):
    def setup(self):
        # Per-tick environment-level metrics. Column names chosen to be
        # SIR-distinct so they exercise abm_auto.calibration COLUMN_ALIASES
        # generality (cross-domain test).
        self.add_environment_property("mean_opinion")
        self.add_environment_property("opinion_variance")
        self.add_environment_property("n_clusters")
