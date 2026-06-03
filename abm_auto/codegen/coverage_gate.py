"""Coverage Gate — the DETERMINISTIC half (ADR-014).

Decides BUILDABILITY (not spec quality): after extraction, can the pipeline
actually generate every mechanism the design declares? Verdict turns on a
deterministic contract match + a verifiability tier — never on architectural
resemblance or the LLM's say-so (ADR-012 anti-fabrication, applied to coverage).

This module is the self-testable core. The LLM half (extracting `Mechanism`
records from DESIGN+spec) is evidence only; it is NOT here. The self-test
below feeds fixture `Mechanism` lists straight in, so the verdict logic is
provable with no LLM — like the operators' self_tests.

Coverage ladder (by build risk):
  operator   — a verified library operator whose contract matches.
  ordinary   — rules / arithmetic the CoderAgent writes safely.
  stdlib     — a named standard algorithm with a known-answer self-test
               codegen can emit (Kalman, tabular-Q, a simple LP). Build+verify.
  uncovered  — deep / custom / no clean oracle. HALT, naming the gap.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── closed vocabularies (the LLM classifies into these; the judge uses them) ──

# A mechanism's capability class.
CAPABILITIES = {
    "learned_predictor",     # supervised item->item / regression net
    "lookup_table",          # static combination/reaction/payoff/transition table
    "population_process",    # birth-death fitness turnover
    "reinforcement_learning",# reward-driven policy/value learning
    "generative_model",      # GAN / VAE / diffusion-net (deep generative)
    "bayesian_filter",       # belief update (Kalman / particle)
    "optimization",          # solves an objective each step (LP / MILP / utility max)
    "market_mechanism",      # auction / order-book / market clearing
    "pde_diffusion",         # continuous spatial field / reaction-diffusion
    "ordinary_logic",        # thresholds, rules, sampling, movement
}

TRAINING_SIGNALS = {"supervised_pairs", "reward_td", "adversarial", "reconstruction", "none"}

# Markers (extracted from DESIGN prose) that force a deterministic reading,
# overriding a (possibly flattening) LLM label.
DEEP_MARKERS = {"adversarial", "multi_network", "generative", "encoder_decoder", "deep_attention"}

# Operators backed by a verified library, keyed by the capability they cover.
OPERATOR_FOR_CAPABILITY = {
    "lookup_table": "RuleTable",
    "population_process": "MoranProcess",
}

# Learned operators carry a CONTRACT TRIPLE; coverage requires an exact match
# (architecture resemblance is NOT enough — this is what stops RL flattening).
LEARNED_CONTRACTS = {
    "FeedforwardLearner": ("single_item", "item_distribution", "supervised_pairs"),
}

# Tier-3 standard algorithms codegen CAN emit a known-answer self-test for.
# Membership here is the deterministic resolution of the fuzzy stdlib tier:
# a mechanism is buildable-and-verifiable iff its named algorithm is here.
VERIFIABLE_STD = {
    "kalman_filter": "track_known_linear_gaussian_signal",
    "tabular_q_learning": "solve_known_mdp",
    "linear_program": "match_known_optimum",
    "finite_difference_diffusion": "conserve_mass_on_known_field",
}


@dataclass(frozen=True)
class Mechanism:
    """One mechanism the model needs (the LLM extracts these; fixtures supply
    them directly). `markers` and `std_algorithm` are the deterministic
    backstops; `faithfulness` is the LLM's cheap self-rating."""
    name: str
    capability: str
    input_kind: str | None = None
    output_kind: str | None = None
    training_signal: str | None = None
    markers: frozenset = frozenset()
    std_algorithm: str | None = None
    faithfulness: str = "full"          # full | partial | none


@dataclass
class CoverageVerdict:
    passed: bool
    tiers: dict                          # name -> (tier, detail)
    uncovered: list                      # names that HALT the pipeline
    build_and_verify: list               # tier-3 names: build, then self-test


def _effective_training_signal(m: Mechanism) -> str | None:
    """Deterministic backstop against a flattening LLM label: DESIGN markers
    override the claimed training_signal. If the prose shows reward/adversarial
    structure, the learner is NOT supervised, whatever the label says."""
    if "adversarial" in m.markers:
        return "adversarial"
    if "reward" in m.markers:
        return "reward_td"
    return m.training_signal


def _resolve_tier3(m: Mechanism) -> tuple[str, str | None]:
    """A mechanism with no operator: buildable iff it names a standard
    algorithm we can emit a known-answer self-test for, else uncovered."""
    if m.std_algorithm in VERIFIABLE_STD:
        return ("stdlib", m.std_algorithm)
    return ("uncovered", None)


def classify(m: Mechanism) -> tuple[str, str | None]:
    """Deterministic tier for one mechanism. Returns (tier, detail)."""
    cap = m.capability
    if cap == "ordinary_logic":
        return ("ordinary", None)
    if cap in OPERATOR_FOR_CAPABILITY:
        return ("operator", OPERATOR_FOR_CAPABILITY[cap])
    if cap == "learned_predictor":
        # anti-flatten: deep markers disqualify any simple learned operator;
        # the contract triple must match exactly (effective signal, not claimed).
        if not (m.markers & DEEP_MARKERS) and m.faithfulness == "full":
            triple = (m.input_kind, m.output_kind, _effective_training_signal(m))
            for op, contract in LEARNED_CONTRACTS.items():
                if triple == contract:
                    return ("operator", op)
        return _resolve_tier3(m)
    # reinforcement_learning, generative_model, bayesian_filter, optimization,
    # market_mechanism, pde_diffusion: no operator today → tier-3 or uncovered.
    return _resolve_tier3(m)


class CoverageGate:
    """Verification Gate (ADR-013/014). PASS iff nothing is uncovered."""

    def check(self, mechanisms: list[Mechanism]) -> CoverageVerdict:
        tiers = {m.name: classify(m) for m in mechanisms}
        uncovered = [n for n, (t, _) in tiers.items() if t == "uncovered"]
        build_and_verify = [n for n, (t, _) in tiers.items() if t == "stdlib"]
        return CoverageVerdict(
            passed=(len(uncovered) == 0),
            tiers=tiers,
            uncovered=uncovered,
            build_and_verify=build_and_verify,
        )


# ── self-test: the six-fixture cross-failure-mode table (ADR-014) + the full
#    set of mechanisms named in the analysis. No LLM. ─────────────────────────

def _fixtures() -> dict:
    """name -> (mechanisms, expected_passed, expected_uncovered_names)."""
    learner = Mechanism("semantic_model", "learned_predictor",
                        "single_item", "item_distribution", "supervised_pairs")
    turnover = Mechanism("moran", "population_process")
    ruletable = Mechanism("recipes", "lookup_table")
    inv = Mechanism("inventory_update", "ordinary_logic")

    gan = Mechanism("conditional_gan", "generative_model",
                    markers=frozenset({"adversarial", "multi_network", "encoder_decoder"}))
    deep_rl = Mechanism("deep_policy", "reinforcement_learning",
                        markers=frozenset({"reward", "multi_network"}))
    tabular_q = Mechanism("q_table", "reinforcement_learning",
                          markers=frozenset({"reward"}), std_algorithm="tabular_q_learning")
    kalman = Mechanism("belief", "bayesian_filter", std_algorithm="kalman_filter")
    particle = Mechanism("particle_belief", "bayesian_filter")            # no oracle
    simple_lp = Mechanism("alloc", "optimization", std_algorithm="linear_program")
    custom_milp = Mechanism("bespoke_milp", "optimization")              # no oracle
    payoff = Mechanism("payoff_matrix", "lookup_table")                  # RuleTable (ordered)
    market = Mechanism("clearing", "market_mechanism")                   # no operator yet
    diffusion = Mechanism("spread", "ordinary_logic")                    # neighbour spread
    # a learner the LLM TRIED to flatten: claims supervised, but prose shows reward
    flattened_rl = Mechanism("sneaky_q", "learned_predictor",
                             "single_item", "item_distribution", "supervised_pairs",
                             markers=frozenset({"reward"}))               # backstop catches it

    return {
        "Yaman": ([learner, turnover, ruletable, inv], True, []),
        "GAN": ([gan], False, ["conditional_gan"]),
        "DeepRL": ([deep_rl], False, ["deep_policy"]),
        "TabularQ": ([tabular_q], True, []),
        "Kalman": ([kalman], True, []),
        "ParticleFilter": ([particle], False, ["particle_belief"]),
        "SimpleLP": ([simple_lp], True, []),
        "CustomMILP": ([custom_milp], False, ["bespoke_milp"]),
        "PayoffGame": ([payoff], True, []),
        "MarketClearing": ([market], False, ["clearing"]),
        "Diffusion": ([diffusion], True, []),
        "FlattenedRL": ([flattened_rl], False, ["sneaky_q"]),   # must NOT pass as operator
    }


def self_test() -> bool:
    """Every mechanism named in the ADR-014 analysis lands in the right tier,
    deterministically. The flatten fixture proves a reward learner mislabelled
    'supervised' is still rejected (the marker backstop overrides the label)."""
    gate = CoverageGate()
    for name, (mechs, want_pass, want_uncovered) in _fixtures().items():
        v = gate.check(mechs)
        if v.passed != want_pass:
            return False
        if sorted(v.uncovered) != sorted(want_uncovered):
            return False
    # tier-3 build+verify routing: Kalman, tabular-Q, simple LP must be flagged
    v = gate.check([_fixtures()["Kalman"][0][0], _fixtures()["TabularQ"][0][0],
                    _fixtures()["SimpleLP"][0][0]])
    if sorted(v.build_and_verify) != sorted(["belief", "q_table", "alloc"]):
        return False
    return True
