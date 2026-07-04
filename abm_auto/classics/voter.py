"""Voter model fixation — a faithful agent-based reproduction (complete graph / well-mixed).

Source: Clifford, P. & Sudbury, A. (1973) "A model for spatial conflict", Biometrika
60(3):581-588 (the original "voter" process). Holley, R.A. & Liggett, T.M. (1975)
"Ergodic theorems for weakly interacting infinite systems and the voter model",
Ann. Probab. 3(4):643-663 (consensus / clustering theory). On the complete graph /
mean field the fixation probability to the all-up state equals the initial up-fraction
u, and the expected magnetization is a martingale (conserved in expectation).

Rules (faithful to the asynchronous / continuous-time voter dynamics, discretised):
  * N agents, each a ``VoterAgent`` carrying a binary opinion in {0, 1}.
  * One UPDATE: pick a uniformly random agent i; pick a uniformly random OTHER agent j
    (j != i, well-mixed / complete graph); set opinion[i] = opinion[j]. The update reads
    only the two agents' own local opinions — there is no global tally consulted to drive
    the copy (the running up-count is kept only as a cheap absorbing-state check + metric,
    not as an input to any agent's decision).
  * One "tick" / sweep = N such asynchronous updates (one update per agent on average).
  * The states all-0 and all-1 are ABSORBING (once everyone agrees, no copy can change
    anything). Run until consensus or a generous sweep cap.
  * Outcome per run = which consensus (all-0 / all-1) + the number of sweeps to reach it.

The classic mean-field result: the fixation probability P(all-up) = u (the initial
up-fraction), and the mean final magnetization m = 2u - 1 is conserved in expectation
(the up-count is a bounded martingale under the symmetric copy rule).

Built on the neutral platform (``abm_auto._platform``): each voter is a ``VoterAgent``
holding its own opinion; the model drives the random-pair updates and uses an
``AgentSet`` only as the agent registry. Given a seed the whole run is reproducible.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from abm_auto._platform import Agent, AgentModel


# -- Agent --------------------------------------------------------------------

class VoterAgent(Agent):
    """One voter holding a binary ``opinion`` in {0, 1}.

    The agent is passive in the asynchronous voter process: it does not ``step`` on a
    schedule. Instead, when the model selects it as the copier i it adopts a randomly
    chosen OTHER agent j's opinion (``adopt``), reading only j's local opinion. ``step``
    is intentionally a no-op so the platform's scheduler is never the driver here.
    """

    def __init__(self, agent_id: int, model: "VoterModel", *, opinion: int = 0) -> None:
        super().__init__(agent_id, model)
        self.opinion = opinion

    def adopt(self, other: "VoterAgent") -> None:
        """Copy another agent's opinion (the voter rule). Reads only ``other.opinion``."""
        self.opinion = other.opinion

    def step(self) -> None:  # asynchronous model: the model drives updates, not a sweep
        pass


# -- Model --------------------------------------------------------------------

class VoterModel(AgentModel):
    """Drives a well-mixed (complete-graph) asynchronous voter model to consensus.

    Construct with N, the initial up-fraction u, and a seed. ``run`` performs
    asynchronous random-pair copy updates (N per sweep) until the population reaches
    an absorbing consensus (all-0 or all-1) or a generous sweep cap, then returns a
    summary dict (which consensus, sweeps to consensus, final up-count / magnetization).
    """

    def __init__(self, *, n: int = 1000, u: float = 0.5, seed: int = 0,
                 max_sweeps: Optional[int] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n < 2:
            raise ValueError(f"n must be >= 2; got {n}")
        if not (0.0 <= u <= 1.0):
            raise ValueError(f"u must be in [0, 1]; got {u}")
        self.n = n
        self.u = u
        # Generous cap: mean-field voter consensus on the complete graph takes O(N)
        # sweeps in expectation; cap well above that so a genuine consensus is never
        # truncated, while a (theoretically impossible) non-absorbing run still halts.
        self.max_sweeps = max_sweeps if max_sweeps is not None else 200 * n

        # Seed exactly round(u*N) up-voters as the first ids; the population is
        # exchangeable on the complete graph, so WHICH ids start up does not matter.
        self.n_up0 = int(round(u * n))
        self.voters: List[VoterAgent] = []
        for k in range(n):
            opinion = 1 if k < self.n_up0 else 0
            v = VoterAgent(k, self, opinion=opinion)
            self.voters.append(v)
            self.add_agent(v)

        # Running up-count: maintained incrementally as a cheap absorbing-state check
        # + magnetization metric. It is NOT consulted by any agent's copy decision.
        self._up = self.n_up0

    # -- metrics --
    def up_count(self) -> int:
        """Number of agents currently holding opinion 1 (the running tally)."""
        return self._up

    def up_count_recount(self) -> int:
        """Independent recount from agent state (used by tests to verify the tally)."""
        return sum(1 for v in self.voters if v.opinion == 1)

    def magnetization(self) -> float:
        """m = (n_up - n_down) / N = 2*(n_up/N) - 1, in [-1, 1]."""
        return (2 * self._up - self.n) / self.n if self.n else 0.0

    def at_consensus(self) -> bool:
        return self._up == 0 or self._up == self.n

    # -- one asynchronous update --
    def update(self) -> None:
        """One asynchronous voter update: random copier i adopts a random OTHER j's
        opinion. Reads only the two agents' local opinions; updates the running tally."""
        i = self.rng.randrange(self.n)
        j = self.rng.randrange(self.n)
        while j == i:
            j = self.rng.randrange(self.n)
        copier = self.voters[i]
        source = self.voters[j]
        before = copier.opinion
        copier.adopt(source)
        after = copier.opinion
        if before != after:
            # only an actual flip changes the tally (+1 if 0->1, -1 if 1->0)
            self._up += 1 if after == 1 else -1

    # -- run --
    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Perform asynchronous updates (N per sweep) until consensus or the cap; return
        the run summary. Consensus is checked after every update so the sweep count
        reflects the partial sweep in which consensus was reached."""
        sweep = 0
        update_in_sweep = 0
        total_updates = 0
        reached = self.at_consensus()  # already-consensus edge case (u in {0, 1})
        while not reached and sweep < self.max_sweeps:
            self.update()
            total_updates += 1
            update_in_sweep += 1
            if update_in_sweep == self.n:
                sweep += 1
                update_in_sweep = 0
            if self.at_consensus():
                reached = True
        # fractional sweeps actually performed (continuous measure of time)
        sweeps_to_consensus = total_updates / self.n
        consensus = None
        if self._up == self.n:
            consensus = 1
        elif self._up == 0:
            consensus = 0
        return {
            "n": self.n,
            "u": self.u,
            "n_up0": self.n_up0,
            "reached_consensus": reached,
            "consensus": consensus,                # 1 = all-up, 0 = all-down, None = capped
            "all_up": consensus == 1,
            "final_up": self._up,
            "final_magnetization": self.magnetization(),
            "total_updates": total_updates,
            "sweeps_to_consensus": sweeps_to_consensus,
            "capped": not reached,
        }


# -- sweep helpers ------------------------------------------------------------

def run_single(*, n: int = 1000, u: float = 0.5, seed: int = 0,
               max_sweeps: Optional[int] = None) -> Dict[str, Any]:
    """One voter run at initial up-fraction u."""
    return VoterModel(n=n, u=u, seed=seed, max_sweeps=max_sweeps).run()


def run_many_seeds(*, n: int = 1000, u: float = 0.5, n_runs: int = 200,
                   seed_base: int = 0, max_sweeps: Optional[int] = None) -> Dict[str, Any]:
    """Run ``n_runs`` independent voter realisations at up-fraction u and summarise.

    Each run uses seed ``seed_base + i`` (deterministic ensemble). Returns the fixation
    frequency P(all-up) = fraction of runs ending all-1, the binomial standard error on
    that frequency, the consensus rate (P1), the mean final magnetization (P3), and
    consensus-time statistics over the runs that reached consensus.
    """
    all_up = 0
    consensus_reached = 0
    mags: List[float] = []
    sweep_times: List[float] = []
    per_run: List[Dict[str, Any]] = []
    for i in range(n_runs):
        seed = seed_base + i
        res = run_single(n=n, u=u, seed=seed, max_sweeps=max_sweeps)
        if res["reached_consensus"]:
            consensus_reached += 1
            sweep_times.append(res["sweeps_to_consensus"])
        if res["all_up"]:
            all_up += 1
        mags.append(res["final_magnetization"])
        per_run.append({
            "seed": seed,
            "consensus": res["consensus"],
            "all_up": res["all_up"],
            "sweeps_to_consensus": res["sweeps_to_consensus"],
            "final_magnetization": res["final_magnetization"],
            "capped": res["capped"],
        })

    p_all_up = all_up / n_runs
    # binomial standard error on the estimated fixation probability
    se_p = (p_all_up * (1.0 - p_all_up) / n_runs) ** 0.5
    consensus_rate = consensus_reached / n_runs
    mean_mag = sum(mags) / len(mags)

    def _stats(xs: List[float]) -> Dict[str, float]:
        if not xs:
            return {"mean": 0.0, "min": 0.0, "max": 0.0, "var": 0.0, "n": 0}
        mean = sum(xs) / len(xs)
        var = sum((x - mean) ** 2 for x in xs) / len(xs)
        return {"mean": mean, "min": min(xs), "max": max(xs), "var": var, "n": len(xs)}

    return {
        "n": n,
        "u": u,
        "n_runs": n_runs,
        "seed_base": seed_base,
        "n_all_up": all_up,
        "p_all_up": p_all_up,
        "se_p_all_up": se_p,
        "n_consensus": consensus_reached,
        "consensus_rate": consensus_rate,
        "mean_final_magnetization": mean_mag,
        "expected_magnetization": 2 * u - 1,
        "consensus_time_sweeps": _stats(sweep_times),
        "per_run": per_run,
    }
