from abm_auto.runtime import NetworkAgent


class Person(NetworkAgent):
    def setup(self):
        # State: 0=S (susceptible), 1=I (infected), 2=R (resistant)
        # Use ints to satisfy Melodie's column-type expectations.
        self.state: int = self._safe_attr("state", 0)
        self.virus_check_timer: int = 0
