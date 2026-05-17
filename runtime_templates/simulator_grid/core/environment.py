from abm_auto.runtime import Environment


class TemplateEnvironment(Environment):
    def setup(self):
        self.count_s: int = 0
        self.count_i: int = 0
        self.count_r: int = 0
