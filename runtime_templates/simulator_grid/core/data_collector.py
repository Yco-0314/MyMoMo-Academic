from abm_auto.runtime import DataCollector


class TemplateDataCollector(DataCollector):
    def setup(self):
        self.add_agent_property("agents", "state")
        self.add_environment_property("count_s")
        self.add_environment_property("count_i")
        self.add_environment_property("count_r")
