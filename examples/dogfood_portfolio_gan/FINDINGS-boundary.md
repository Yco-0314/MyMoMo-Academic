# Boundary dogfood — conditional GAN (finance ABM). My prediction MISSED.

Ran abm-auto's design phase (reproduce mode) on a faithful story for Scholl et
al. (ICAIF'25), a 4-component conditional GAN for fund-manager strategies.
Pre-registered in `dogfood_design.py`. n=1.

## Pre-registration vs reality — I was WRONG

**Predicted:** the design phase hits the learned-operator ceiling and either
(a) flattens the GAN onto FeedforwardLearner, (b) piles up AI-ASSUMPTION tags,
or (c) the viability gate rejects it.

**Actual:** none of those. raw AI-ASSUMPTION = 7, hardened = 4 → **gate PASS**.
FeedforwardLearner: 0 mentions (NOT flattened). The design *faithfully*
described the full GAN — GAN 13×, discriminator 13×, adversarial 8×, VAE 5×,
attention 3× — as an ABM with `FundManager` agents and four neural components
(`MarketVAE`, `StrategyEncoder`, `PortfolioAllocator`, `Discriminator`),
tagging it all `[paper-canonical]` (hence few assumptions).

I record the miss per the project's discipline: predictions are locked before
the run and scored honestly, hits or misses.

## The real finding: the gate FALSE-PASSES an unbuildable model

The design passes viability but **cannot be built by the pipeline**:

- the mechanism methods are stubs — `encode_strategy()` → `pass`,
  `generate_portfolio()` → `pass` (DESIGN.md lines 124, 129);
- it references four deep neural component classes the runtime does NOT
  provide and the template generator does NOT emit (`MarketVAE`,
  `StrategyEncoder`, `PortfolioAllocator`, `Discriminator` in a phantom
  `core/components/`);
- it calls methods that do not exist: `discriminator.train_step(...)`,
  `self._train_generator()`, `agents.setup_agents(from_csv=...)`.

The CoderAgent would have to hand-write a full conditional GAN (VAE + attention
+ adversarial training) from scratch — exactly the failure the W2 wall
documented, now quadrupled. There is no GAN operator; FeedforwardLearner (one
hidden layer) is nowhere near it.

## Why it slips through: there is no buildability / operator-coverage gate

The viability gate checks specification QUALITY (assumption count, the 8
required elements, an LLM judge) — NOT BUILDABILITY. A deep-ML model can be
perfectly well-specified ("all paper-canonical") yet impossible for the
pipeline to generate. So it sails through design + viability and would only
break downstream: extraction (the typed `MechanismSpec` has no slot that can
hold a 4-component GAN — only the `LearnedOperator` = FeedforwardLearner slot)
and codegen (CoderAgent stubs `pass` or hallucinates a GAN).

This is the genuinely useful result of the cross-domain test: it exposed a GAP
in the harness, not in the operators. The pipeline lacks an **operator-coverage
check** — after extraction, verify every learned/complex mechanism maps to a
PROVIDED operator (or plainly generatable code); if a mechanism needs an
operator that does not exist (a GAN), HALT honestly with "needs operator X"
instead of passing a design that codegen will stub out.

## Honest conclusions

1. **The learned-operator approach has a ceiling.** It covers a simple
   trainable predictor (FeedforwardLearner). A conditional GAN (generator +
   discriminator + VAE + attention, adversarially trained) is far past it. The
   fix is NOT to lower a gate; it is either a (large) GAN operator or an
   honest coverage-halt.
2. **The viability gate measures spec quality, not buildability** — and for
   deep-ML methods these diverge. An operator-coverage gate after extraction
   is the missing piece this dogfood found.
3. **This paper was never a reproduction target** (proprietary CRSP + fund
   data, a deep generative model, not a simulation ABM). The value was the
   boundary test: it found where the system silently over-promises.
