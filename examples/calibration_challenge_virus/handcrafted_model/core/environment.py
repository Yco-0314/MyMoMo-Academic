import random

from abm_auto.runtime import Environment


class VirusEnvironment(Environment):
    def setup(self):
        pass

    def step(self, agents, network, scenario):
        """Execute one tick: spread virus + recovery checks.

        Algorithm (from Milan calibration_challenge.pdf):
          1. Each infected agent has chance virus_spread_chance/100 to infect
             each non-resistant neighbour (susceptible only — resistant immune).
          2. At intervals of virus_check_frequency ticks, each infected agent
             rolls recovery: with chance recovery_chance/100, recovers.
          3. On recovery, with chance gain_resistance_chance/100, becomes R;
             otherwise reverts to S.
        """
        spread_p = scenario.virus_spread_chance / 100.0
        recover_p = scenario.recovery_chance / 100.0
        resist_p = scenario.gain_resistance_chance / 100.0
        check_every = int(scenario.virus_check_frequency)

        # ── 1. Spread ──
        # Snapshot infected list first so newly-infected this tick don't act yet
        infected = [a for a in agents if a.state == 1]
        for src in infected:
            neighbours = network.get_neighbors(src)
            for nb in neighbours:
                if nb.state == 0 and random.random() < spread_p:
                    nb.state = 1
                    nb.virus_check_timer = 0

        # ── 2. Recovery checks ──
        for a in agents:
            if a.state != 1:
                continue
            a.virus_check_timer += 1
            if a.virus_check_timer >= check_every:
                a.virus_check_timer = 0
                if random.random() < recover_p:
                    a.state = 2 if random.random() < resist_p else 0
