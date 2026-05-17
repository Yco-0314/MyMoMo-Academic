"""
End-to-end integration test with mocked LLM.

Proves the entire pipeline framework runs without errors:
- Workspace creation & artifact management
- Agent call chain (designer → coder → verifier → analyzer → optimizer → reporter)
- SALib sensitivity analysis (sampling + index computation)
- Trajectory analysis (clustering + correlation)
- Memory system (ingest + retrieve + knowledge extraction)
- Reviewer panel flow
- Language switching (zh / en)

Run: uv run python tests/test_e2e_mock.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Mock LLM responses ──────────────────────────────────────────────────────

MOCK_DESIGN = """# ABM Design

## Part 1: Model Overview
- **Project Name**: SIR_Epidemic
- **Agents**: Person (states: S, I, R)
- **Environment**: 20x20 grid
- **Key Parameters**: infection_rate=0.3, recovery_rate=0.1, num_agents=100

## Part 2: Behavioral Rules
- Susceptible agents become infected with probability infection_rate on contact
- Infected agents recover with probability recovery_rate each step
"""

MOCK_ODD = """# ODD Protocol: SIR_Epidemic

## 1. Purpose and Patterns
Simulate epidemic spread dynamics.

## 2. Entities, State Variables, and Scales
- Person agents with state (S/I/R), position (x,y)
- 20x20 grid, 100 time steps

## 3. Process Overview and Scheduling
Each step: move → contact → infect → recover

## 4. Design Concepts
Emergence: epidemic curve shape emerges from individual interactions.

## 5. Initialization
Random placement, 5 initially infected.

## 6. Input Data
None.

## 7. Submodels
Contact model: Moore neighborhood.
"""

MOCK_CODE = """=== FILE: core/agent.py ===
from Melodie import Agent
class Person(Agent):
    def setup(self):
        self.state = 'S'
    def step(self):
        pass

=== FILE: core/model.py ===
from Melodie import Model
class SIRModel(Model):
    def setup(self):
        pass
    def step(self):
        pass

=== FILE: core/environment.py ===
from Melodie import Environment
class SIREnvironment(Environment):
    pass

=== FILE: core/scenario.py ===
from Melodie import Scenario
class SIRScenario(Scenario):
    pass

=== FILE: core/data_collector.py ===
from Melodie import DataCollector
class SIRCollector(DataCollector):
    pass

=== FILE: main.py ===
print("Simulation complete")

=== FILE: data/input/SimulatorScenarios.csv ===
id,infection_rate,recovery_rate,num_agents
0,0.3,0.1,100
"""

MOCK_ANALYSIS = """## Run 1 Analysis
### Key Findings
- 60% of agents infected at peak
- Epidemic peaks at step 15
### Parameter Sensitivity
- infection_rate is the dominant driver
### Theory Alignment
- Matches standard SIR dynamics
### Anomalies
- None
### Recommended Next Steps
- Increase infection_rate to 0.5
"""

MOCK_OPTIMIZE = json.dumps({
    "hypothesis": "Higher infection rate leads to earlier peak",
    "parameters": {"infection_rate": 0.5},
    "rationale": "Testing upper bound of infection dynamics"
})

MOCK_REPORT = "# SIR Epidemic Report\n\nThis study examined..."

MOCK_KNOWLEDGE = json.dumps([
    {"key": "infection_threshold", "knowledge": "infection_rate > 0.4 triggers outbreak", "confidence": 0.6, "category": "pattern"}
])

MOCK_REVIEW = """## Reviewer 1: Theory Review
### Score: 6/10
### Fatal flaws:
1. No theoretical framework
"""

MOCK_EDITOR = """## Editor Decision
### 90 Second Test: Pass
### Score: 24/40
### Verdict: Major Revision
"""

# Map prompt names to responses
RESPONSE_MAP = {
    "phase1_design": MOCK_DESIGN,
    "odd": MOCK_ODD,
    "phase2_code": MOCK_CODE,
    "verify_fix": MOCK_CODE,
    "analyze": MOCK_ANALYSIS,
    "optimize": MOCK_OPTIMIZE,
    "report": MOCK_REPORT,
    "report_en": MOCK_REPORT,
    "sensitivity": "Sensitivity interpretation: infection_rate is most influential.",
    "trajectory": "Trajectory interpretation: two behavioral modes detected.",
    "extract_knowledge": MOCK_KNOWLEDGE,
    "peer_review": MOCK_REVIEW,
    "review_theory": MOCK_REVIEW,
    "review_methodology": MOCK_REVIEW,
    "review_literature": MOCK_REVIEW,
    "review_logic": MOCK_REVIEW,
    "review_editor": MOCK_EDITOR,
}


def mock_call_llm(self, system, user, max_tokens=8192):
    """Mock LLM that returns pre-set responses based on prompt content."""
    # Check system prompt for agent type hints
    if "ABM Engineer" in system or "FILE:" in system:
        return MOCK_CODE
    for key, response in RESPONSE_MAP.items():
        if key in user[:500].lower() or key.replace("_", " ") in user[:500].lower():
            return response
    # Default: return something parseable
    if "JSON" in system or "json" in user[:200]:
        return MOCK_OPTIMIZE
    return MOCK_ANALYSIS


# ── Test helpers ─────────────────────────────────────────────────────────────

def create_mock_workspace(tmp: Path) -> Path:
    """Create a workspace with fake simulation outputs."""
    ws = tmp / "workspace" / "test_run"
    ws.mkdir(parents=True)
    (ws / "results").mkdir()

    # STORY.md
    story = (PROJECT_ROOT / "examples" / "sir_epidemic" / "story.md").read_text()
    (ws / "STORY.md").write_text(story)

    return ws


def create_fake_results(ws: Path, n_runs: int = 5):
    """Generate fake CSV results for multiple runs."""
    params_history = []
    for i in range(1, n_runs + 1):
        run_dir = ws / "results" / f"run_{i:02d}"
        run_dir.mkdir(parents=True, exist_ok=True)

        rate = 0.2 + (i - 1) * 0.15
        steps = 50
        t = np.arange(steps)
        infected = (rate * 80 * np.sin(t / 10) + 30 + np.random.normal(0, 2, steps)).clip(0, 100)

        df = pd.DataFrame({
            "step": t,
            "infected_count": infected,
            "recovered_count": 100 - infected,
        })
        df.to_csv(run_dir / "agent_data.csv", index=False)

        params_history.append({
            "run": i,
            "params": {"infection_rate": rate, "recovery_rate": 0.1},
            "hypothesis": f"Test rate={rate:.2f}",
        })

    (ws / "params_history.json").write_text(json.dumps(params_history, indent=2))

    # SimulatorScenarios.csv for SALib
    model_dir = ws / "model" / "data" / "input"
    model_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"id": 0, "infection_rate": 0.3, "recovery_rate": 0.1, "num_agents": 100}]).to_csv(
        model_dir / "SimulatorScenarios.csv", index=False
    )

    return params_history


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.fixture
def r():
    return Results()


class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def check(self, name, condition, detail=""):
        if condition:
            self.passed += 1
            print(f"  ✓ {name}")
        else:
            self.failed += 1
            self.errors.append(f"{name}: {detail}")
            print(f"  ✗ {name} — {detail}")


def test_imports(r: Results):
    """Test all module imports."""
    print("\n[1/8] Module Imports")
    modules = [
        "abm_auto.cli", "abm_auto.config", "abm_auto.pipeline",
        "abm_auto.runner.workspace", "abm_auto.runner.executor",
        "abm_auto.agents.base", "abm_auto.agents.designer",
        "abm_auto.agents.coder", "abm_auto.agents.verifier",
        "abm_auto.agents.analyzer", "abm_auto.agents.optimizer",
        "abm_auto.agents.reporter", "abm_auto.agents.odd_writer",
        "abm_auto.agents.salib_optimizer", "abm_auto.agents.reviewer",
        "abm_auto.analysis.trajectory_analyzer", "abm_auto.memory.store",
    ]
    for mod in modules:
        try:
            __import__(mod)
            r.check(mod, True)
        except Exception as e:
            r.check(mod, False, str(e))


def test_workspace(r: Results):
    """Test workspace CRUD operations."""
    print("\n[2/8] Workspace Operations")
    from abm_auto.runner.workspace import Workspace

    ws = Workspace.create("_test_ws")
    r.check("create workspace", ws.path.exists())

    ws.write_story("# Test Story")
    r.check("write story", ws.read_story() == "# Test Story")

    ws.write_design("# Test Design")
    r.check("write design", ws.read_design() == "# Test Design")

    ws.write_model_files({"test.py": "print('hello')"})
    r.check("write model files", (ws.model_dir / "test.py").exists())

    files = ws.read_model_files()
    r.check("read model files", "test.py" in files)

    ws.append_params_history(run=1, params={"a": 1}, hypothesis="test")
    history = ws.read_params_history()
    r.check("params history", len(history) == 1 and history[0]["params"]["a"] == 1)

    run_dir = ws.results_for_run(1)
    r.check("results dir", run_dir.exists())

    ws.write_report("# Report")
    r.check("write report", ws.report_path.exists())

    # Cleanup
    shutil.rmtree(ws.path, ignore_errors=True)


def test_memory(r: Results):
    """Test 3-tier experiment memory."""
    print("\n[3/8] Experiment Memory")
    from abm_auto.memory.store import ExperimentMemory

    tmp = Path(tempfile.mkdtemp()) / "memory"
    mem = ExperimentMemory(tmp)

    # Working
    mem.working.set("key1", "value1", priority=0.8)
    r.check("working set/get", mem.working.get("key1") == "value1")

    # Episodic
    mem.ingest_run(run_id=1, params={"a": 1}, metrics={"m": 10}, hypothesis="h1")
    mem.ingest_run(run_id=2, params={"a": 2}, metrics={"m": 20}, hypothesis="h2")
    r.check("episodic ingest", len(mem.episodic.all()) == 2)
    r.check("episodic by_run", mem.episodic.by_run(1).metrics["m"] == 10)

    stats = mem.episodic.summary_stats()
    r.check("episodic stats", "m" in stats and stats["m"]["mean"] == 15.0)

    # Semantic
    mem.add_knowledge("k1", "pattern 1", confidence=0.6, source_runs=[1])
    mem.add_knowledge("k1", "pattern 1 updated", confidence=0.8, source_runs=[2])
    entry = mem.semantic.get("k1")
    r.check("semantic upsert", entry.confidence == 0.8 and 2 in entry.source_runs)

    # Context retrieval
    ctx = mem.retrieve_context()
    r.check("retrieve context", len(ctx) > 50 and "当前" in ctx)

    # Persistence
    mem2 = ExperimentMemory(tmp)
    r.check("persistence", mem2.working.get("key1") == "value1")

    shutil.rmtree(tmp.parent, ignore_errors=True)


def test_trajectory_analyzer(r: Results):
    """Test trajectory analysis with synthetic data."""
    print("\n[4/8] Trajectory Analyzer")
    from abm_auto.analysis.trajectory_analyzer import TrajectoryAnalyzer

    tmp = Path(tempfile.mkdtemp())
    create_fake_results(tmp, n_runs=5)

    ta = TrajectoryAnalyzer(tmp)
    result = ta.analyze()

    r.check("analysis runs", result is not None)
    r.check("total runs", result.total_runs == 5)
    r.check("clusters found", len(result.clusters) >= 2)
    r.check("critical timesteps", len(result.critical_timesteps) > 0)
    r.check("param correlations", len(result.param_correlations) >= 1)

    # Check output files
    r.check("trajectory_analysis.md", (tmp / "trajectory_analysis.md").exists())
    r.check("trajectory_analysis.json", (tmp / "trajectory_analysis.json").exists())

    summary = result.to_summary()
    r.check("summary non-empty", len(summary) > 100)

    shutil.rmtree(tmp, ignore_errors=True)


def test_salib_sampling(r: Results):
    """Test SALib sample generation (no simulation needed)."""
    print("\n[5/8] SALib Sampling")
    from SALib.sample import morris as morris_sample, sobol as sobol_sample

    problem = {
        "num_vars": 3,
        "names": ["infection_rate", "recovery_rate", "num_agents"],
        "bounds": [[0.1, 0.6], [0.05, 0.2], [50, 200]],
    }

    # Morris
    samples_m = morris_sample.sample(problem, N=10)
    r.check("morris sampling", samples_m.shape[0] > 0 and samples_m.shape[1] == 3)

    # Sobol
    samples_s = sobol_sample.sample(problem, N=8, calc_second_order=True)
    r.check("sobol sampling", samples_s.shape[0] > 0 and samples_s.shape[1] == 3)

    # Morris analyze (with fake Y)
    from SALib.analyze import morris as morris_analyze
    Y = np.random.randn(samples_m.shape[0])
    Si = morris_analyze.analyze(problem, samples_m, Y)
    r.check("morris analyze", "mu_star" in Si and len(Si["mu_star"]) == 3)

    # Sobol analyze
    from SALib.analyze import sobol as sobol_analyze
    Y2 = np.random.randn(samples_s.shape[0])
    Si2 = sobol_analyze.analyze(problem, Y2, calc_second_order=True)
    r.check("sobol analyze", "S1" in Si2 and len(Si2["S1"]) == 3)


def test_agent_chain_mock(r: Results):
    """Test the full agent chain with mocked LLM."""
    print("\n[6/8] Agent Chain (Mock LLM)")

    with patch("abm_auto.agents.base.BaseAgent.call_llm", mock_call_llm):
        from abm_auto.runner.workspace import Workspace
        from abm_auto.agents.designer import DesignAgent
        from abm_auto.agents.coder import CoderAgent
        from abm_auto.agents.analyzer import AnalyzerAgent
        from abm_auto.agents.optimizer import OptimizerAgent
        from abm_auto.agents.reporter import ReporterAgent
        from abm_auto.agents.odd_writer import OddWriter
        from abm_auto.runner.executor import Executor

        client = MagicMock()
        ws = Workspace.create("_test_agents")

        # Write story
        story = (PROJECT_ROOT / "examples" / "sir_epidemic" / "story.md").read_text()
        ws.write_story(story)

        try:
            # Designer
            designer = DesignAgent(client, ws, model="mock")
            designer.run()
            r.check("designer → DESIGN.md", ws.design_path.exists())

            # ODD Writer
            odd = OddWriter(client, ws, model="mock")
            odd.run()
            r.check("odd_writer → ODD.md", (ws.path / "ODD.md").exists())

            # Coder
            coder = CoderAgent(client, ws, model="mock")
            coder.run()
            r.check("coder → model files", len(ws.read_model_files()) > 0)

            # Create fake results for analyzer
            create_fake_results(ws.path, n_runs=1)

            # Analyzer
            executor = Executor(ws)
            analyzer = AnalyzerAgent(client, ws, model="mock")
            insights = analyzer.run(executor, 1)
            r.check("analyzer → insights", len(insights) > 0)

            # Optimizer
            optimizer = OptimizerAgent(client, ws, model="mock")
            result = optimizer.run(1, insights, coder)
            r.check("optimizer → params", isinstance(result, dict))

            # Reporter (zh)
            reporter = ReporterAgent(client, ws, model="mock", lang="zh")
            report = reporter.run([insights])
            r.check("reporter zh → report", ws.report_path.exists())

            # Reporter (en)
            reporter_en = ReporterAgent(client, ws, model="mock", lang="en")
            report_en = reporter_en.run([insights])
            r.check("reporter en → report", len(report_en) > 0)

        finally:
            shutil.rmtree(ws.path, ignore_errors=True)


def test_reviewer_panel_mock(r: Results):
    """Test the 5-reviewer panel with mocked LLM."""
    print("\n[7/8] Reviewer Panel (Mock LLM)")

    with patch("abm_auto.agents.base.BaseAgent.call_llm", mock_call_llm):
        from abm_auto.runner.workspace import Workspace
        from abm_auto.agents.reviewer import ReviewerAgent

        client = MagicMock()
        ws = Workspace.create("_test_review")

        try:
            # Populate workspace with artifacts
            story = (PROJECT_ROOT / "examples" / "sir_epidemic" / "story.md").read_text()
            ws.write_story(story)
            ws.write_design(MOCK_DESIGN)
            (ws.path / "ODD.md").write_text(MOCK_ODD)
            ws.write_report(MOCK_REPORT)
            create_fake_results(ws.path, n_runs=3)

            # Panel review
            reviewer = ReviewerAgent(client, ws, model="mock")
            combined = reviewer.run(mode="panel")
            r.check("panel review runs", len(combined) > 100)
            r.check("review_r1.md", (ws.path / "review_r1.md").exists())
            r.check("review_r2.md", (ws.path / "review_r2.md").exists())
            r.check("review_r3.md", (ws.path / "review_r3.md").exists())
            r.check("review_r4.md", (ws.path / "review_r4.md").exists())
            r.check("review_editor.md", (ws.path / "review_editor.md").exists())
            r.check("peer_review.md", (ws.path / "peer_review.md").exists())

            # Quick review
            shutil.rmtree(ws.path / "peer_review.md", ignore_errors=True)
            quick = reviewer.run(mode="quick")
            r.check("quick review runs", len(quick) > 0)

        finally:
            shutil.rmtree(ws.path, ignore_errors=True)


def test_lang_switching(r: Results):
    """Test language directive injection."""
    print("\n[8/8] Language Switching")
    from abm_auto.agents.base import BaseAgent, LANG_DIRECTIVES

    r.check("en directive exists", "en" in LANG_DIRECTIVES)
    r.check("zh directive exists", "zh" in LANG_DIRECTIVES)
    r.check("en contains English", "English" in LANG_DIRECTIVES["en"])
    r.check("zh contains 中文", "中文" in LANG_DIRECTIVES["zh"])

    # Verify agent stores lang
    client = MagicMock()
    from abm_auto.runner.workspace import Workspace
    ws = Workspace(Path(tempfile.mkdtemp()))

    agent_en = BaseAgent(client, ws, lang="en")
    agent_zh = BaseAgent(client, ws, lang="zh")
    r.check("agent lang en", agent_en.lang == "en")
    r.check("agent lang zh", agent_zh.lang == "zh")

    shutil.rmtree(ws.path, ignore_errors=True)


def test_sanity_checker(r: Results):
    """Test sanity checker catches degenerate output."""
    print("\n[9/9] Sanity Checker")
    from abm_auto.agents.sanity_checker import SanityChecker

    # Create a degenerate Environment CSV (constant count_i=0)
    tmp = Path(tempfile.mkdtemp())
    csv_path = tmp / "Result_Simulator_Environment.csv"
    df_bad = pd.DataFrame({
        "id_scenario": [0]*10, "id_run": [0]*10, "period": list(range(10)),
        "count_s": [500]*10, "count_i": [0]*10, "count_r": [0]*10,
    })
    df_bad.to_csv(csv_path, index=False)

    warnings = SanityChecker.check_run([csv_path])
    r.check("detects constant columns", len(warnings) > 0)
    r.check("mentions count_i", any("count_i" in w for w in warnings))

    # Create a healthy Environment CSV (varying counts)
    csv_good = tmp / "Result_Simulator_Environment_good.csv"
    df_good = pd.DataFrame({
        "id_scenario": [0]*10, "id_run": [0]*10, "period": list(range(10)),
        "count_s": [500, 498, 490, 470, 440, 400, 350, 300, 260, 230],
        "count_i": [0, 2, 10, 25, 45, 70, 90, 80, 50, 20],
        "count_r": [0, 0, 0, 5, 15, 30, 60, 120, 190, 250],
    })
    df_good.to_csv(csv_good, index=False)

    warnings_good = SanityChecker.check_run([csv_good])
    r.check("healthy output passes", len(warnings_good) == 0)

    shutil.rmtree(tmp, ignore_errors=True)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("ABM-AUTO End-to-End Integration Test (Mock LLM)")
    print("=" * 60)

    r = Results()

    test_imports(r)
    test_workspace(r)
    test_memory(r)
    test_trajectory_analyzer(r)
    test_salib_sampling(r)
    test_agent_chain_mock(r)
    test_reviewer_panel_mock(r)
    test_lang_switching(r)
    test_sanity_checker(r)

    print("\n" + "=" * 60)
    print(f"RESULTS: {r.passed} passed, {r.failed} failed")
    print("=" * 60)

    if r.errors:
        print("\nFailed tests:")
        for e in r.errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("\n✓ ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
