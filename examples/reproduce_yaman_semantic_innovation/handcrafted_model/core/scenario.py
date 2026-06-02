"""Scenario = one cell of the Yaman experiment.

Every field is overridable per-row from data/input/SimulatorScenarios.csv,
so the synergy design (P_semantic x P_social) is just a set of rows.

Parameter names map to the paper (SI Table 1 & 2):
  p_semantic   = P_S   probability of using the semantic model (vs random)
  p_social     = P_SL  probability of attempting social learning
  p_generalize = P_G   probability of the generalization strategy
  agent_num    = N     population size            {25, 50, 100}, default 50
  n_attempts   = n_attempts per generation        {5, 10, 15},  default 10
  embed_dim/hidden_dim                            {8, 16, 32},  default 16
  learning_rate                                   0.001 (FeedforwardLearner default)

Defaults are the paper's main-text (bolded) values where known; the few
the PDF leaves to "the code provided with the paper" (max generations,
train_epochs/generation) are flagged ASSUMPTION and set to sane values.
"""
from abm_auto.runtime import Scenario


class YamanScenario(Scenario):
    def setup(self):
        # ── run control ────────────────────────────────────────────────
        self.periods = 150          # number of generations (ASSUMPTION: paper says "max(Gen)", value in code)
        self.agent_num = 50         # N population size (paper main-text default)
        self.n_attempts = 10        # attempts per generation (paper: "out of a maximum of 10")
        self.seed = 0

        # ── strategy mix (the experiment knobs) ────────────────────────
        self.p_semantic = 0.0       # P_S
        self.p_social = 0.0         # P_SL
        self.p_generalize = 0.0     # P_G

        # ── semantic model shape (FeedforwardLearner) ──────────────────
        self.embed_dim = 16
        self.hidden_dim = 16
        # CORRECTED after run 1: lr=0.001 (the FeedforwardLearner default; the
        # PDF defers lr to "the code") left M stuck at the uniform distribution
        # — falsified by probe_semantic.py (loss ~ ln(184), sampled valid-
        # partner rate = chance). lr=0.2 demonstrably learns the co-occurrence
        # structure (sampled valid-partner rate ~39x base). Faithfulness fix,
        # not a tune-to-win: a semantic model that cannot learn is not the
        # paper's semantic model.
        self.learning_rate = 0.2
        self.train_epochs = 20      # updateModels epochs/generation (ASSUMPTION: not in PDF)
