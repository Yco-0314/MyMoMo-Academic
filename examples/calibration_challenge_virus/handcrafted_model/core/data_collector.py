from abm_auto.runtime import DataCollector


class VirusDataCollector(DataCollector):
    def setup(self):
        # Per-period environment-level counts. Column names chosen to match
        # what the Milan MSE benchmark looks for (count_s/i/r aliases).
        self.add_environment_property("count_s")
        self.add_environment_property("count_i")
        self.add_environment_property("count_r")
