# Reproduce: Learning fund-manager strategies as a conditional GAN

Based on Scholl, Mahfouz, Calinescu & Farmer, "Learning to Manage Investment
Portfolios beyond Simple Utility Functions" (ICAIF'25). The goal is to model a
population of mutual-fund managers as agents whose strategy is a *learned
conditional distribution over portfolio weights*, rather than a hand-specified
utility function — producing diverse, realistic agents for market simulation.

## The agents

Each agent is a fund manager. A manager's strategy is a conditional
probability distribution over next-period portfolio weights:

    p(w_t | w_{t-1}, X_{t-1}, r_{t-T..t-1}, phi_a)

where `w` are portfolio weights over N=500 stocks, `X` are K asset
characteristics, `r` is a history of T periods of returns, and `phi_a` is an
8-dimensional latent vector encoding manager a's strategy.

## The mechanism: a conditional Generative Adversarial Network (GAN)

The model is a conditional GAN with four trained neural components:

1. **Market model** — a variational autoencoder that generates synthetic stock
   universes (X-hat, r-hat) for N=500 stocks, with the Carhart four-factor
   model (market, SMB size, HML value, UMD momentum) embedded structurally:
   returns are r = alpha + sum_k beta_k y_k + epsilon. The encoder maps real
   market states to latent factor shocks via attention over return
   cross-sections; the decoder samples synthetic characteristics and returns.

2. **Strategy encoder** E_phi — maps an observed portfolio allocation to the
   8-dim latent strategy phi through three parallel attention lanes:
   characteristics+weights -> factor-exposure (phi 1-4); returns ->
   performance (phi 5-6); weight changes -> trading style (phi 7-8). Each lane
   uses normalization, dense dimensionality reduction, and multi-head
   attention.

3. **Portfolio allocator (decoder)** D_w — generates portfolio weights
   conditioned on the market state, the latent strategy phi, and previous
   weights, producing valid sparse allocations.

4. **Discriminator** — distinguishes real (portfolio, market) tuples from
   generated ones; trained adversarially against the generator.

## Training and data

The generator and discriminator are trained adversarially on a dataset of
1436 U.S. equity mutual funds' quarterly holdings, with Carhart factor
loadings precomputed from CRSP. The learned 8-dim latent space should recover
known investment styles (e.g. "growth" vs "value") and reveal implicit
manager objectives.

## What to reproduce

The qualitative finding: the learned latent strategy space captures
recognizable fund styles, and sampling latent strategies yields diverse,
realistic synthetic portfolios conditioned on market state.
