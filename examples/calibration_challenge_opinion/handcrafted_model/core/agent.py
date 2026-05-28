from abm_auto.runtime import NetworkAgent


class Citizen(NetworkAgent):
    def setup(self):
        # Continuous opinion in [0, 1]; loaded from CSV when present (initial
        # condition seeding), else uniform random per agent.
        self.opinion: float = self._safe_attr("opinion", 0.5)
