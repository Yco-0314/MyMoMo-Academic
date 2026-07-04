"""Genuine agent-based department coordination-response simulation (v3).

Replaces v2's central two-pass god-loop with autonomous ``DepartmentAgent``s on
the neutral ABM platform (``abm_auto._platform``: AgentSet scheduler +
DataCollector). Each department is one agent per network node with LOCAL state and
LOCAL rules only — no global view, no central scheduler over tasks.

The key v3 mechanism is **network-gated activation propagation**: a task activates
from ITS OWN lead, and the *environment* (this model) computes the least-latency
arrival of that signal at every node via a Dijkstra over the CURRENT topology — an
edge of weight ``w`` costing ``ceil(1/w)`` ticks (heavier edge => sooner) — into a
model-owned message bus that agents only READ once ``arrival <= t`` (see
``receive``/``_refresh_activation``). This is a leak-free, distributed-EQUIVALENT
bus: arrivals are numerically identical to faithful per-agent hop-by-hop relay, but
the propagation is computed centrally, not literally relayed agent-to-agent (the
agents themselves are autonomous and act only on their local inbox). The arrival
tick of a task's signal at a shared collaborator therefore depends on the path from
that task's lead through the current edge set. Adding
edges can pull several tasks' arrivals into the SAME tick window at a shared hub
(e.g. 省交通运输厅, a collaborator on multiple phase-2 tasks) => peak concurrency
RISES => overload => that hub's tasks slow. This makes ``peak_overload`` EMERGENT
and treatment-varying — the channel v2 lacked (v2 synchronized all phase-2 tasks
via a single shared eligible_tick regardless of topology).

Deterministic given a seed. Non-spatial (space=None); no hazard physics.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import networkx as nx

from abm_auto._platform import AgentSet, DataCollector, Agent, StagedAgentModel
from abm_auto.coord._network import CoordNetwork, _HUBS


@dataclass
class Department:
    """Config record for a department actor (capacity / failure profile). The live
    per-tick agent is ``DepartmentAgent``; this dataclass stays importable and is
    accepted as the optional ``depts`` override on ``CoordModel``."""
    name: str
    capacity: float = 3.0
    response_delay: int = 1
    failure_prob: float = 0.03
    priority: float = 1.0
    load: float = 0.0  # demanded work this tick (reset per tick); MAY exceed capacity


@dataclass
class Task:
    name: str
    lead: str
    collaborators: List[str]
    work: float
    phase: str
    needs: List[str]
    trigger_tick: int


@dataclass
class Scenario:
    # NOTE (audit 2026-06-28): `triggers` is currently INERT — activation timing comes
    # solely from Task.trigger_tick + DAG `needs` (see _activation_origin). Kept for
    # API/back-compat; emptying it does not change any result.
    triggers: Dict[int, List[str]]      # tick -> task names (currently unused; see note)
    edge_cuts: Dict[int, list]          # tick -> [(u,v), ...] edges disabled from then on


class DepartmentAgent(Agent):
    """One autonomous department, one per network node. LOCAL state + LOCAL rules
    (no central task scheduler/oracle: the agent acts only on its own inbox + capacity).

    inbox : task_name -> first tick this department received that task's activation
            signal. The arrival ticks are computed centrally by the model into a
            leak-free message bus (see CoordModel._refresh_activation); the agent only
            reads the entries whose arrival has elapsed — distributed-EQUIVALENT to,
            but not literally, per-agent relay.
    load  : work committed THIS tick (reset each tick) — emergent, MAY exceed
            capacity (=> overload).
    """

    def __init__(self, agent_id: int, model: "CoordModel", name: str,
                 capacity: float, failure_prob: float) -> None:
        super().__init__(agent_id, model)
        self.name = name
        self.capacity = capacity
        self.failure_prob = failure_prob
        self.inbox: Dict[str, int] = {}
        self.load: float = 0.0

    # ---- per-agent stages (run in scheduled order by the StagedAgentModel) ----

    def receive(self) -> None:
        """Stage 1 — drain newly-arrived activation signals into the local inbox.

        The model precomputes, for the current topology, the tick each task's
        signal first reaches each node (per-task, from that task's OWN lead). Here
        the agent records arrivals up to the current tick into its own inbox; it
        does NOT see the global schedule — only what has reached it."""
        m = self.model
        for tname, arr in m._arrival.get(self.name, {}).items():
            if arr <= m.t and tname not in self.inbox:
                self.inbox[tname] = arr

    def decide(self) -> None:
        """Stage 2 — decide which tasks this dept is engaged with and commit load.

        Engaged (``_actionable``) = tasks this dept leads or collaborates on whose
        ``needs`` are all done AND whose activation signal has reached it (in inbox).
        Engagement spans the task's whole active duration (the lead must keep driving
        it; a collaborator stays available so the lead is never blocked).

        LOAD is concentrated, not flat. A LEAD bears the task's load for its whole
        duration (it owns the work). A COLLABORATOR bears load only during a short
        COORDINATION WINDOW of ``COORD_WINDOW`` ticks right after the task's activation
        reaches it (the handshake/sync burst), then it is merely on call. This is the
        v3 mechanism change that makes overload edge-responsive: a shared hub (e.g.
        省交通运输厅, collaborator on 3 phase-2 tasks) overloads only when several of
        those coordination windows OVERLAP, and whether they overlap depends on the
        arrival-tick spread, which is itself topology-dependent (see _activation_origin
        + _refresh_activation). When several phase-2 tasks gate on the SAME predecessor
        but their leads sit at different network distances from that predecessor's lead,
        their activations arrive staggered; adding edges can pull those arrivals into
        the same window (peak RISES) or stagger them further (peak FALLS) — so peak load
        VARIES by treatment instead of being pinned at #collaborator-tasks. (A flat,
        whole-duration collaborator load — the v2 / first-v3 behaviour — pins the peak
        because the long task durations make all the windows overlap regardless of the
        few-tick arrival spread.) Throttling/failure is applied in ``act`` once every
        dept's load for the tick is known."""
        self.load = 0.0
        m = self.model
        self._actionable = []  # task names this dept is ENGAGED with THIS tick
        for tname in m._tasks_touching.get(self.name, ()):  # tasks where I am lead or collab
            t = m.tasks[tname]
            r = m.results[tname]
            if r["status"] in ("done", "failed"):
                continue
            if m.t < t.trigger_tick:
                continue
            if any(m.results[d]["status"] != "done" for d in t.needs):
                continue  # (redundant with inbox below: _activation_origin returns None
                          #  until every predecessor is done, so a task cannot reach the
                          #  inbox earlier — kept as a defensive, readable local guard)
            if tname not in self.inbox:           # activation has not reached me yet
                continue
            self._actionable.append(tname)
            if t.lead == self.name:
                # the lead owns the work: bears load every tick it drives the task
                self.load += min(m.task_rate, r["remaining"])
            else:
                # a collaborator bears load only during the coordination window right
                # after activation arrived (concentrated sync effort, then on call)
                arrived = self.inbox[tname]
                if m.t - arrived < m.coord_window:
                    self.load += min(m.task_rate, r["remaining"])

    def act(self) -> None:
        """Stage 3 — apply throttled progress to each actionable task I touch.

        Effective progress is throttled by MY overload (load/capacity > 1 slows
        me); the lead's overload raises failure probability. A task advances only
        when BOTH its lead and every reachable collaborator have committed to it
        this tick (so a single overloaded hub bottlenecks the whole task)."""
        m = self.model
        if self.load > self.capacity:
            m._tick_overloaded = True
        for tname in self._actionable:
            t = m.tasks[tname]
            r = m.results[tname]
            if t.lead != self.name:
                continue  # the LEAD drives the task; collaborators only contribute load
            actors = [t.lead] + [c for c in t.collaborators]
            # every actor must have this task actionable this tick (all committed load)
            actor_agents = [m.dept_agents[a] for a in actors if a in m.dept_agents]
            if any(tname not in ag._actionable for ag in actor_agents):
                continue
            if r["status"] == "pending":
                r["status"] = "active"
                r["start_tick"] = m.t
            demand = min(m.task_rate, r["remaining"])
            # congestion = worst actor overload across this task's actors; >1 throttles
            congestion = max((ag.load / ag.capacity for ag in actor_agents if ag.capacity > 0),
                             default=1.0)
            step = demand / max(1.0, congestion)
            lead_ag = m.dept_agents[t.lead]
            lead_overload = max(0.0, lead_ag.load / lead_ag.capacity - 1.0)
            fail_p = max(lead_ag.failure_prob, m.slope * lead_overload)
            if m.rng.random() < min(fail_p, 0.95):
                step *= 0.5  # failed step: half progress (retry cost)
            r["remaining"] -= step
            if r["remaining"] <= 1e-9:
                r["status"] = "done"
                r["done_tick"] = m.t


class CoordModel(StagedAgentModel):
    """Agent-based coordination model on the neutral platform. Public surface is
    v2-identical: ``CoordModel(net, tasks, scenario, *, seed, ...)`` and
    ``.run() -> {task: {status,start_tick,done_tick}, "_peak_overload": float}``.
    """

    MAX_TICKS = 500

    #: per-tick work each ACTIVE task demands from every actor (lead + collaborators).
    TASK_RATE = 1.0
    #: A department can comfortably handle ONE coordination at a time (demand 1.0 <
    #: capacity) but is overloaded by TWO concurrent ones (demand 2.0 > capacity).
    #: Hubs are scarcer still (they appear in many tasks). Calibrated to
    #: mechanism-functionality ("a dept in >=2 concurrent tasks overloads") — NOT
    #: to any optimized-vs-original-vs-null outcome.
    HUB_CAPACITY = 1.3
    NONHUB_CAPACITY = 1.6

    #: Coordination window (ticks): how long a COLLABORATOR bears a task's load after
    #: that task's activation reaches it — the concentrated handshake/sync burst, after
    #: which the collaborator is merely on call (the LEAD bears load for the whole
    #: duration). This is what makes overload edge-responsive: a shared hub overloads
    #: only when several coordination windows OVERLAP, and the arrival-tick spread that
    #: governs overlap is topology-dependent. Set so the window is SHORTER than a typical
    #: task's active duration (otherwise long durations make all windows overlap and pin
    #: the peak, the v2/first-v3 defect). Calibrated to mechanism-functionality (a few-
    #: tick handshake), NOT to any optimized-vs-original-vs-null outcome.
    COORD_WINDOW = 2

    stages = ("receive", "decide", "act")

    def __init__(self, net: CoordNetwork, tasks: List[Task], scenario: Scenario, *,
                 seed: int, depts: Dict[str, Department] | None = None,
                 overload_failure_slope: float = 0.4, task_rate: float | None = None,
                 coord_window: int | None = None):
        super().__init__(space=None, seed=seed)
        self.net = net
        self.tasks = {t.name: t for t in tasks}
        self.scenario = scenario
        self._dept_cfg = depts or self._default_depts(net)
        self.slope = overload_failure_slope
        self.task_rate = self.TASK_RATE if task_rate is None else task_rate
        self.coord_window = self.COORD_WINDOW if coord_window is None else coord_window

        # ---- build the autonomous agents on the platform ----
        self.dept_agents: Dict[str, DepartmentAgent] = {}
        for i, n in enumerate(net.nodes):
            cfg = self._dept_cfg.get(n) or Department(n, capacity=self._cap_for(n))
            ag = DepartmentAgent(i, self, n, cfg.capacity, cfg.failure_prob)
            self.dept_agents[n] = ag
            self.add_agent(ag)

        # which tasks each department touches (lead or collaborator) — local view seed
        self._tasks_touching: Dict[str, List[str]] = {n: [] for n in net.nodes}
        for tname, t in self.tasks.items():
            for who in [t.lead] + list(t.collaborators):
                if who in self._tasks_touching:
                    self._tasks_touching[who].append(tname)

        # run-state
        self.results: Dict[str, dict] = {
            n: {"status": "pending", "start_tick": None, "done_tick": None, "remaining": t.work}
            for n, t in self.tasks.items()}
        self._g = net.graph()
        self._origin: Dict[str, Optional[int]] = {n: None for n in self.tasks}  # activation origin tick
        self._arrival: Dict[str, Dict[str, int]] = {n: {} for n in net.nodes}   # node -> task -> arrival tick
        self._peak_overload = 0.0
        self._tick_overloaded = False

        # per-tick load collector (emergent peak_overload derives from this series)
        self.reporter = DataCollector({
            "max_util": lambda m: max((a.load / a.capacity for a in m.dept_agents.values()
                                       if a.capacity > 0), default=0.0),
        })

    # ---- config ----

    def _cap_for(self, n: str) -> float:
        return self.HUB_CAPACITY if n in _HUBS else self.NONHUB_CAPACITY

    def _default_depts(self, net: CoordNetwork) -> Dict[str, Department]:
        """Hubs get tighter capacity (shared across many tasks); non-hubs get more.
        Calibrated to mechanism-functionality (overload CAN occur under concurrency),
        NOT to any cross-treatment outcome."""
        return {n: Department(n, capacity=self._cap_for(n)) for n in net.nodes}

    # ---- activation propagation (network-gated, per-task from each task's lead) ----

    def _edge_cost(self, w: float) -> int:
        """Hop cost of an edge of weight ``w``: ceil(1/w) ticks (heavier => sooner,
        min 1). This is the per-hop relay latency of the activation message."""
        if w <= 0:
            return self.MAX_TICKS
        return max(1, math.ceil(1.0 / w))

    def _hop_distance(self, src: str) -> Dict[str, int]:
        """Shortest relay latency (in ticks) from ``src`` to every node over the
        CURRENT edge set, summing per-edge cost ceil(1/w). Hop-by-hop relay =>
        fastest path = least total latency. Unreachable nodes are omitted."""
        if src not in self._g:
            return {src: 0}
        return nx.single_source_dijkstra_path_length(self._g, src, weight=self._dijkstra_cost)

    def _dijkstra_cost(self, u, v, data) -> int:
        return self._edge_cost(data.get("weight", 0.0))

    def _activation_origin(self, t: Task) -> Optional[int]:
        """The tick a task's activation ORIGINATES at its OWN lead — i.e. when this
        lead has been *notified* that the task may begin.

        MECHANISM (v3, end-to-end network-gated activation, NOT a global broadcast):
        a task with predecessors does not activate at the abstract global tick those
        predecessors completed. Each predecessor's completion is a signal emitted by
        that predecessor's OWN lead; it relays hop-by-hop over the current topology to
        this task's lead, taking ``relay(pred_lead -> this_lead)`` ticks. The origin is
        therefore the LATEST-arriving predecessor notification:

            origin = max over needs of (pred_done_tick + relay(pred_lead -> lead))

        This is why origins are edge-responsive and can desynchronize by topology: the
        phase-2 tasks share predecessor 预警发布 but their leads sit at DIFFERENT network
        distances from 预警发布's lead (省气象局), so they are notified at different ticks,
        and that spread shifts as edges are added/cut. (v2 — and the first v3 cut —
        used a single global completion tick for all dependents, collapsing the spread
        to the lead->hub hop difference (0-1 tick), far smaller than a task's duration,
        so peak concurrency was structurally pinned regardless of topology.)

        A root task (no needs) originates at its trigger tick. Returns None until the
        origin can be determined (trigger not reached, or some predecessor not done /
        not yet reachable from the predecessor's lead)."""
        if self.t < t.trigger_tick:
            return None
        if not t.needs:
            return t.trigger_tick
        origin = t.trigger_tick
        for d in t.needs:
            pred = self.tasks[d]
            pr = self.results[d]
            if pr["status"] != "done" or pr["done_tick"] is None:
                return None  # predecessor not finished -> no notification yet
            relay = self._hop_distance(pred.lead).get(t.lead)
            if relay is None:
                return None  # predecessor's lead cannot reach this lead on current topology
            origin = max(origin, pr["done_tick"] + max(0, relay))
        return origin

    def _refresh_activation(self) -> None:
        """Recompute, on the CURRENT topology, the first tick each task's activation
        signal reaches each node. A task's signal ORIGINATES at its OWN lead (see
        ``_activation_origin`` — origin propagates over the topology from predecessor
        leads) and then relays hop-by-hop to every node; arrival at node v = origin +
        hop_distance(lead -> v). Per-task from its own lead — so a shared collaborator's
        arrival ticks differ by task and shift with topology (the desynchronizing
        mechanism). Recomputed each tick so newly-completed predecessors release
        dependents' signals and edge changes re-time them.

        CACHE CAVEAT (audit 2026-06-28): once set, ``_origin`` is not raised and
        ``_arrival`` accumulates monotone-min, so a LATER edge_cut that *lengthens* an
        already-open relay path would not delay a stale-early arrival. The locked study
        uses ``edge_cuts={}`` (static / edge-adding topology only), so no result is
        affected; revisit this if edge-cut scenarios are ever exercised."""
        for tname, t in self.tasks.items():
            origin = self._origin[tname]
            if origin is None:
                origin = self._activation_origin(t)
                if origin is None or origin > self.t:
                    continue
                self._origin[tname] = origin
            dist = self._hop_distance(t.lead)
            for node, d in dist.items():
                arr = origin + max(0, d)
                prev = self._arrival[node].get(tname)
                if prev is None or arr < prev:
                    self._arrival[node][tname] = arr

    # ---- tick lifecycle (StagedAgentModel hooks) ----

    def begin_step(self) -> None:
        # apply scheduled edge cuts, then refresh activation on the current topology
        for (u, v) in self.scenario.edge_cuts.get(self.t, []):
            if self._g.has_edge(u, v):
                self._g.remove_edge(u, v)
        self._refresh_activation()
        self._tick_overloaded = False

    def end_step(self) -> None:
        # mark tasks whose activation can never reach the lead/a collaborator as failed
        self._fail_unreachable()

    def _fail_unreachable(self) -> None:
        """A task fails if, with its activation origin open, its lead cannot relay a
        signal to some collaborator on the current topology (no path) — the
        coordination link is structurally absent, matching v2's unreachable-fails
        semantics."""
        for tname, t in self.tasks.items():
            r = self.results[tname]
            if r["status"] in ("done", "failed"):
                continue
            if self._origin[tname] is None:
                continue
            dist = self._hop_distance(t.lead)
            if any(c not in dist for c in t.collaborators):
                r["status"] = "failed"

    # ---- run ----

    def run(self) -> dict:
        self.reporter.collect(self)  # t=0 baseline (all loads 0)
        for _ in range(self.MAX_TICKS):
            self.step()  # StagedAgentModel.step: begin -> stages -> end -> collect -> t+=1
            util = self.reporter.records[-1]["max_util"]
            if util > self._peak_overload:
                self._peak_overload = util
            if all(self.results[n]["status"] in ("done", "failed") for n in self.tasks):
                break
        return {
            **{n: {"status": r["status"], "start_tick": r["start_tick"], "done_tick": r["done_tick"]}
               for n, r in self.results.items()},
            "_peak_overload": round(self._peak_overload, 4),
        }
