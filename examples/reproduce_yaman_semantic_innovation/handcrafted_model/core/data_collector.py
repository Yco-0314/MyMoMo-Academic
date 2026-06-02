"""Per-generation environment metrics. `repertoire_size` is the paper's
headline dependent variable (distinct non-base items the population holds)."""
from abm_auto.runtime import DataCollector


class YamanDataCollector(DataCollector):
    def setup(self):
        self.add_environment_property("repertoire_size")
        self.add_environment_property("max_level")
        self.add_environment_property("mean_score")
        self.add_environment_property("max_score")
        self.add_environment_property("mean_inventory")
