# Classic-ABM Reproductions — Roadmap to 100 (models 51–100)
> Planning document. NOT a build order yet — the user has approved generating this roadmap only; building is deferred to a later decision.
**Generated:** 2026-07-01, via a multi-domain inventory workflow (10 parallel domain scouts → dedup/synthesis → adversarial completeness-critic).
**Provenance:** 81 raw candidates proposed across 11 domains → 59 distinct retained after dedup → grouped into 14 themed batches (71 entries; margin above the 50 needed). Critic verdict: reaching 100 is realistic.
## The discipline carries over unchanged
Every model below is to be built lock-first: write `PREDICTIONS-locked.md` (predictions **and** the grading metric) and commit it BEFORE running; never tune a parameter to make a clause pass; a falsified clause is an honest **MISS**, not a failure to hide; fair controls (only one variable differs); seed-averaging so RNG noise can't masquerade as signal; and **framing disclosed honestly** — only models marked *genuine-agent* claim autonomous agent-stepping; *CA / network-gen / signed-net / hybrid* are disclosed as such in the module docstring and FINDINGS (as already done for BTW, OFC, Heider, ER/BA/WS, etc.).
## Framing mix of the candidate pool
| framing | count |
|---|---|
| genuine-agent | 43 |
| CA (disclose) | 13 |
| hybrid (disclose) | 8 |
| network-gen (disclose) | 7 |

Genuine-agent dominates (43/71); the CA / network-gen / hybrid entries are the ones whose disclosure matters most.
## Feasibility verdict (adversarial critic, verbatim)
> Reaching 100 distinct study-grade reproductions is realistic: 50 are built and the roadmap supplies 70 more candidates, so even after pruning the ~5-6 over-similar/assembly entries flagged above there is comfortable headroom (50 + ~64 survivors = ~114) to pick a clean 100. Idea supply and per-model coding effort are NOT the bottleneck — the genuine bottleneck is review/distinctness adjudication and honest lock-first gate design. Many later entries (submodularity proofs, percolation-threshold equivalences, SOC universality-class exponents) are correct-but-adjacent results whose 'reproduction' value collapses unless each gets a quantitative gate that a built model's rerun could NOT already pass; that adversarial-review capacity, not the number 100, is the constraint. Watch also the framing drift: batches 11-12 lean heavily on 'network-generation' generators (Molloy-Reed, Price, Holme-Kim) that are structurally one family and risk being scored as one reproduction each when they are really parameter variants of preferential attachment / degree-sequence sampling.
## The batches (51–100, with margin)
Batch numbering continues the suite (the built suite is through batch 6). Framing + difficulty are the scout/synth calls; the P-sketches are lockable starting points, to be finalized in each model's locked doc.

### Batch 7 — Opinion dynamics beyond the voter model

**`q_voter`** — Castellano, Munoz & Pastor-Satorras 2009 — Nonlinear q-voter model (2009)
*framing:* genuine-agent · *difficulty:* medium
*claim:* q agreeing neighbors per flip yields a nonlinear exit probability (continuous transition for q<=2, discontinuous with hysteresis for q>=4), unlike the linear voter.
*lockable predictions (draft):*
  - P1: For q=1 the model reduces to the linear voter: exit probability E(x) is linear in initial up-fraction x with |E(x)-x|<=0.05 across x in {0.2,0.5,0.8}.
  - P2: For q=2 the exit probability is nonlinear/S-shaped: E(0.5)=0.5 by symmetry but |E(0.3)-0.3|>=0.08, bending off the q=1 straight line.
  - P3: For q>=4 with noise the stationary magnetization shows a discontinuous jump and hysteresis (loop width in the noise parameter > 0.05), absent for q<=2.
*vs nearest built:* Nearest built is voter (linear, q=1). q-voter requires q agreeing neighbors per flip, producing nonlinear exit probabilities and, for large q, a discontinuous/hysteretic transition the linear voter cannot show.

**`noisy_voter_kirman`** — Carro, Toral & San Miguel 2016 / Granovsky-Madras 1995 — Noisy voter model (2016)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Spontaneous flipping destroys the absorbing states, giving a finite-size order-disorder transition: bimodal/herding for a*N<1, unimodal for a*N>1, with a_c~1/N.
*lockable predictions (draft):*
  - P1: Bimodal for weak noise: for a*N < 1 the stationary distribution of magnetization is bimodal (peaks away from 0, edge mass > center mass).
  - P2: Unimodal for strong noise: for a*N > 1 the distribution is unimodal and centered at m=0 (Gaussian-like, single peak).
  - P3: The crossover noise scales inversely with system size: a_c * N is approximately constant (within a factor 2) across N in {100, 400, 1600}.
*vs nearest built:* Nearest built is voter (absorbing, no noise). The noisy voter adds a spontaneous-flip rate that destroys the absorbing states, giving an ergodic stationary distribution with a finite-size order-disorder transition at a_c ~ 1/N — a feature absent from both the plain voter and from Kirman (which uses pairwise recruitment, not voter copying).

**`abrams_strogatz_language`** — Abrams & Strogatz 2003 — Modelling the dynamics of language death (Nature) (2003)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Two languages cannot stably coexist: a status-driven unstable interior fixed point means one always dies and the higher-status language survives.
*lockable predictions (draft):*
  - P1: Coexistence is unstable: starting from x near 0.5 with s != 0.5, the speaker fraction converges to 0 or 1 in >95% of runs (no stable interior equilibrium).
  - P2: Higher-status language wins: with status s>0.5 the fraction speaking it reaches >0.95 whenever its initial share exceeds the unstable fixed point x* = s^(1/a)/(s^(1/a)+(1-s)^(1/a))... predicted basin boundary within +/-0.05 of measured.
  - P3: For equal status s=0.5 the outcome is symmetric: P(language A wins) = 0.5 +/- 0.07 and the fixed point sits at x*=0.5.
*vs nearest built:* Nearest built is voter/Sznajd (binary, symmetric, no status). Abrams-Strogatz adds an asymmetric status parameter s and volatility exponent a with a nonlinear attractiveness P ~ x^a, giving a status-driven unstable interior fixed point rather than density-conserving drift.

**`coda_continuous_opinions`** — Martins 2008 — Continuous opinions and discrete actions (CODA) (2008)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Bayesian updating of hidden continuous beliefs from observed discrete actions drives opinions to certainty (extremism) and stable spatial domains, inverting bounded-confidence moderation.
*lockable predictions (draft):*
  - P1: Opinions extremize: the mean absolute log-odds (confidence) grows without bound — median |log-odds| at t=10^4 sweeps exceeds 5 (i.e. p>0.99 or p<0.01) for the majority of agents.
  - P2: Extremism is local-structure driven: on a 2D lattice agents form spatial domains of agreeing extremists; like-action neighbor fraction > 0.85 at late times.
  - P3: Action consensus need NOT be global: multiple stable opinion domains coexist (>=2 macroscopic domains persist) while each agent is individually near-certain.
*vs nearest built:* Nearest built is Deffuant/HK (continuous opinions, bounded confidence, convergence to moderate clusters). CODA inverts this: agents exchange only discrete actions and Bayesian-update hidden continuous beliefs, so opinions diverge to certainty (extremism) instead of averaging toward moderation.

**`social_impact_theory`** — Nowak, Szamrej & Latane 1990 — From private attitudes to public opinion (1990)
*framing:* genuine-agent · *difficulty:* high
*claim:* Under Latane's strength*sqrt(N)/distance^2 impact rule, society does not reach consensus: minorities survive in stable spatial clusters with no agent movement.
*lockable predictions (draft):*
  - P1: The minority is not eliminated: starting from a 30% minority, the final minority fraction stays > 0.10 (clusters persist, no full consensus) in >80% of runs.
  - P2: Spatial clustering increases: the like-neighbor fraction (local opinion correlation) rises from ~0.5 (random) to > 0.75 at the frozen state.
  - P3: The dynamics freeze into a stable configuration: after equilibration, < 2% of agents change opinion per sweep (metastable clustered state, not ongoing churn).
*vs nearest built:* Nearest built is Schelling (spatial clustering by relocation) and voter (consensus). Social impact keeps agents fixed and flips opinions by a distance-weighted strength*immediacy*number rule (sqrt(N), 1/d^2), producing minority survival and clustering without movement and without reaching consensus.

### Batch 8 — Epidemics and influence on networks

**`sirs_waning_immunity`** — Hethcote 2000 — The mathematics of infectious diseases (SIRS) (2000)
*framing:* genuine-agent · *difficulty:* low
*claim:* Waning immunity (R->S) replaces SIR burnout with a stable nonzero endemic equilibrium for R0>1; endemic level rises with the waning rate.
*lockable predictions (draft):*
  - P1: Threshold preserved: endemic prevalence i* < 0.01 for R0=0.8; i* > 0.05 for R0=2.0 (averaged over the late window).
  - P2: Waning sustains endemicity: with omega>0, long-run prevalence settles to a NONZERO plateau (late-window mean i* > 0.02 at R0=2.0), whereas the omega=0 (SIR) control decays to i*≈0 (<0.005).
  - P3: Monotone endemic level: late-window i* is non-decreasing in omega across {0, 0.01, 0.05, 0.1} at fixed R0=2.0; i*(omega=0.1) > i*(omega=0.01).
*vs nearest built:* Nearest built are sir (no reinfection; one outbreak then extinction) and sis (no immune R state). SIRS keeps a transient immune compartment AND allows return to S, producing a stable endemic equilibrium distinct from both SIR burnout and SIS dynamics.

**`maki_thompson_rumor`** — Maki & Thompson 1973 — rumor spreading (ignorant/spreader/stifler) (1973)
*framing:* genuine-agent · *difficulty:* medium
*claim:* A rumor has no spreading threshold; the deterministic stop-rule yields a universal ~0.203 never-reached fraction regardless of rate, unlike SIR.
*lockable predictions (draft):*
  - P1: No threshold: even at very low spreading rate the final ever-heard fraction (1 - ignorant) > 0.5 (a finite rumor outbreak occurs for all rate>0, unlike SIR which dies below R0=1).
  - P2: Universal never-heard limit: in the fast-spreading regime the final fraction of agents who NEVER hear the rumor converges to 0.20 +/- 0.03, matching the transcendental root of x=exp(-2(1-x)).
  - P3: Stifler dominance: at fixed point essentially all agents are ignorant-or-stifler and spreaders ->0 (spreader fraction <0.01), with stifler fraction > ignorant fraction in the high-rate regime.
*vs nearest built:* Nearest built is sir (same 3-state I/R-like structure) and bass_diffusion. The Maki-Thompson stop-rule (spreader->stifler on contacting any non-ignorant) is fundamentally different from recovery: it removes the epidemic threshold entirely and yields the 0.203 never-reached constant, which SIR cannot produce.

**`bikhchandani_information_cascade`** — Bikhchandani, Hirshleifer & Welch 1992 — Informational cascades (1992)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Sequential Bayesian agents herd after two same-direction predecessors, ignoring private signals; cascades are near-certain, can lock onto the wrong action, and are fragile.
*lockable predictions (draft):*
  - P1: Cascade onset: with signal accuracy p=0.7, the probability that an informational cascade has formed by agent N=20 exceeds 0.9.
  - P2: Cascades can be wrong: conditional on the true state, the fraction of cascades that lock onto the INCORRECT action is bounded away from 0 (between 0.05 and 0.40 at p=0.7) — i.e. herding is not asymptotically efficient.
  - P3: Accuracy monotonicity: probability of a CORRECT cascade increases with signal accuracy p across {0.55,0.65,0.75,0.85}; P_correct(0.85) - P_correct(0.55) > 0.15.
*vs nearest built:* Nearest built are bass_diffusion and granovetter_threshold (mechanistic adoption, no Bayesian inference). BHW agents do sequential BAYESIAN belief updating on private signals + observed history; the wrong-cascade / fragility result is an information-economics phenomenon absent from every built spreading/adoption model.

**`pastor_satorras_vespignani_sis`** — Pastor-Satorras & Vespignani 2001 — Epidemic spreading in scale-free networks (2001)
*framing:* genuine-agent · *difficulty:* medium
*claim:* SIS on a scale-free network has a vanishing epidemic threshold (lambda_c->0 as N->inf) while a homogeneous graph keeps a finite threshold.
*lockable predictions (draft):*
  - P1: On BA network, measured epidemic threshold lambda_c(N) decreases monotonically as N grows over {1e3,3e3,1e4,3e4}; ratio lambda_c(3e4)/lambda_c(1e3) < 0.5 (trending to 0).
  - P2: On random-regular/ER graph of equal mean degree, lambda_c(N) stays roughly constant: lambda_c(3e4)/lambda_c(1e3) within [0.7,1.4] (finite threshold, no vanishing).
  - P3: Just above threshold, endemic prevalence rho(lambda) on BA grows continuously from 0 with no finite jump (rho(lambda_c+0.05)<0.1), consistent with the predicted exponential/algebraic onset rather than a mean-field square-root law.
*vs nearest built:* Nearest built is sis (well-mixed endemic SIS) and barabasi_albert (graph generation only). This couples SIS dynamics ONTO a heterogeneous network and tests the vanishing-threshold / topology-dependence claim, which neither well-mixed sis nor the static BA generator addresses.

**`newman_network_sir_final_size`** — Newman 2002 — Spread of epidemic disease on networks (bond percolation) (2002)
*framing:* genuine-agent · *difficulty:* medium
*claim:* SIR maps to bond percolation: outbreak iff T>T_c=<k>/(<k^2>-<k>); degree heterogeneity lowers T_c and final size equals the percolated giant component.
*lockable predictions (draft):*
  - P1: Percolation threshold: measured outbreak-size takeoff occurs near T_c=<k>/(<k^2>-<k>); large-outbreak probability <0.1 for T=0.7*T_c and >0.5 for T=1.5*T_c on a configuration-model graph.
  - P2: Heterogeneity lowers threshold: on a high-variance degree distribution (e.g. power-law) the measured T_c is strictly below that of a Poisson graph with the same mean degree (ratio < 0.8).
  - P3: Final size = percolation cluster: above threshold, the mean fraction infected in large outbreaks matches the giant-component fraction of the bond-percolated graph within +/-10%.
*vs nearest built:* Nearest built are sir (well-mixed) and erdos_renyi (giant-component percolation on a static graph). This fuses the two: SIR transmission ON a heterogeneous network with the T_c=<k>/(<k^2>-<k>) percolation-threshold and giant-component final-size claims, which neither the well-mixed sir nor the contagion-free erdos_renyi giant-component study tests.

**`independent_cascade`** — Kempe, Kleinberg & Tardos 2003 — Independent Cascade influence maximization (2003)
*framing:* genuine-agent · *difficulty:* medium
*claim:* The influence function is monotone submodular, so greedy seed selection achieves >=(1-1/e) of optimal and beats degree-centrality heuristics.
*lockable predictions (draft):*
  - P1: Submodularity (diminishing returns): the marginal gain of adding the k-th greedy seed is non-increasing in k (marginal_gain[k+1] <= marginal_gain[k] within Monte-Carlo noise) for all k in the budget.
  - P2: Greedy beats heuristics: for a fixed seed budget B, greedy expected spread >= 1.10x the spread of the best degree-centrality seed set on a BA graph.
  - P3: (1-1/e) floor: greedy spread / (best achievable upper-bound proxy) >= 0.63 across budgets B in {1,5,10}.
*vs nearest built:* Nearest built are watts_cascade and complex_contagion (fixed-rule spreading, no seed optimization). Independent Cascade adds per-edge stochastic activation AND an algorithmic seed-selection objective; the load-bearing claim is submodularity / the (1-1/e) greedy guarantee, which no built spreading model evaluates.

### Batch 9 — Evolution of cooperation and reciprocity

**`stag_hunt`** — Skyrms 2004 / Kandori-Mailath-Rob 1993 — risk-dominance selection (2004)
*framing:* genuine-agent · *difficulty:* low
*claim:* In the stag-hunt coordination game, local imitation on a lattice selects the risk-dominant (hare) equilibrium from random starts even though stag Pareto-dominates.
*lockable predictions (draft):*
  - P1: When hare is risk-dominant (stag payoff a, with (a-... ) basin < 1/2, e.g. a=3,b(temptation safe)=2,c=0,d=1 giving stag basin < 0.5), >80% of random-start lattice runs converge to all-hare.
  - P2: There is a basin threshold p_c near 0.5 in initial stag fraction: runs starting above p_c go to all-stag, below go to all-hare, with the crossover within +/-0.1 of the risk-dominance prediction.
  - P3: Well-mixed replicator dynamics give an unstable interior fixed point at the risk-dominance ratio; trajectories diverge to whichever absorbing state the initial condition lies on the correct side of.
*vs nearest built:* Nearest built are hawk_dove (anti-coordination, single mixed ESS) and coord_response_v3 (diffusion-style coordination). Stag hunt is a PURE coordination game with two strict Nash equilibria and a Pareto-vs-risk tension; the lockable result is equilibrium SELECTION (risk-dominance wins), absent from any built model.

**`snowdrift_game`** — Hauert & Doebeli 2004 — Spatial structure inhibits cooperation in the snowdrift game (2004)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Lattice structure REDUCES cooperation below the well-mixed f*=1-r for the snowdrift payoff ordering — the sign-flip opposite of the spatial PD.
*lockable predictions (draft):*
  - P1: Well-mixed mean-field run converges to cooperator fraction f* = 1 - r within +/-0.03 (e.g. r=0.5 -> f*~0.50, r=0.8 -> f*~0.20).
  - P2: On an L>=50 lattice with imitation/best-response updating, spatial cooperator fraction is LOWER than the well-mixed f* for r >= 0.4 (spatial - wellmixed <= -0.05).
  - P3: The spatial-vs-wellmixed cooperation gap is sign-flipped from the PD case: snowdrift gap negative for most r, whereas a matched spatial PD shows a positive cooperation gap.
*vs nearest built:* Nearest built is nowak_may_pd (spatial PD where structure HELPS cooperation) and hawk_dove (well-mixed ESS only). Differs by using the snowdrift/chicken payoff ordering (T>R>S>P) on a lattice and reproducing the counterintuitive REVERSED result that space hurts cooperation — a direct A/B contrast against nowak_may_pd.

**`pavlov_wsls`** — Nowak & Sigmund 1993 — Win-stay-lose-shift outperforms tit-for-tat (1993)
*framing:* genuine-agent · *difficulty:* medium
*claim:* In the noisy iterated PD, win-stay-lose-shift displaces TFT: it both corrects errors and exploits unconditional cooperators, becoming the modal strategy.
*lockable predictions (draft):*
  - P1: Head-to-head in noisy IPD (error rate ~0.01), WSLS achieves strictly higher mean payoff than TFT against a mixed background (WSLS payoff - TFT payoff > 0).
  - P2: Starting from a TFT-dominated population with mutation, WSLS becomes the modal strategy at long times (WSLS share > 0.5, and > TFT share by > 0.2).
  - P3: WSLS exploits ALLC (unconditional cooperators) — against ALLC, WSLS mean payoff exceeds TFT mean payoff vs ALLC, demonstrating the exploit-suckers property that distinguishes it from TFT.
*vs nearest built:* Nearest is axelrod_ipd (Axelrod-tournament strategies incl. TFT). Pavlov/WSLS is a specific one-bit memory automaton whose lockable claim is a STRATEGY-RANKING reversal (WSLS > TFT under noise) plus the error-correction + sucker-exploitation mechanism, a result Axelrod's deterministic tournament does not produce.

**`image_scoring_reciprocity`** — Nowak & Sigmund 1998 — Evolution of indirect reciprocity by image scoring (1998)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Indirect-reciprocity cooperation evolves and is stable iff the probability of knowing a recipient's image score exceeds the cost-to-benefit ratio (q>c/b).
*lockable predictions (draft):*
  - P1: For fixed c/b (e.g. c=0.1,b=1 -> c/b=0.1), cooperation level rises sharply as q crosses ~0.1; mean cooperation > 0.5 for q > c/b + 0.1 and < 0.2 for q < c/b - 0.05.
  - P2: The cooperation-onset threshold q_c tracks c/b across at least two c/b values (|q_c - c/b| <= 0.1 for c/b in {0.1, 0.3}).
  - P3: Discriminator (image-threshold) strategy share exceeds unconditional-defector share at steady state whenever q > c/b (discriminators are the dominant strategy above threshold).
*vs nearest built:* Nearest is axelrod_ipd (DIRECT reciprocity, repeated dyads) and ethnocentrism (tag-based, no individual reputation). Image scoring is INDIRECT reciprocity: cooperation toward a third party based on an observable reputation score, with the distinct closed-form threshold q > c/b that neither built model captures.

**`ultimatum_game_fairness`** — Nowak, Page & Sigmund 2000 — Fairness versus reason in the Ultimatum Game (2000)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Reputation drives evolution toward fair offers (p* well above the rational p->0); anonymity collapses offers to near-rational low values.
*lockable predictions (draft):*
  - P1: Anonymous (no reputation) treatment: evolved mean offer p* converges low, p* < 0.25 (toward the rational p->0 limit).
  - P2: Reputation treatment (probability w of knowing opponent's acceptance threshold high, w>=0.5): evolved mean offer rises to a fair range, p* > 0.35, and acceptance threshold q* > 0.25.
  - P3: Fair-offer level increases monotonically with reputation probability w (Pearson r between w and evolved p* > 0.8 across a w-sweep).
*vs nearest built:* No bargaining/fairness game exists in the suite; nearest is moran_process/wright_fisher (neutral genetics, no strategic payoff) and hawk_dove (ESS in a contest). Ultimatum game is a two-role bargaining game whose lockable claim is the reputation-driven emergence of FAIRNESS, structurally unlike any built contest or coordination model.

### Batch 10 — Spatial games, tags and networked cooperation

**`tag_cooperation_riolo`** — Riolo, Cohen & Axelrod 2001 — Evolution of cooperation without reciprocity (2001)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Continuous-tag similarity matching alone sustains high (~0.74) donation rates with cyclic tag-cluster turnover, with no reciprocity, reputation or space.
*lockable predictions (draft):*
  - P1: Baseline (donation cost c=0.1, benefit 1, tolerance mutation present): mean donation rate at steady state > 0.6 (paper reports ~0.74).
  - P2: Cooperation requires the cost ratio below a bound: donation rate collapses (< 0.3) when cost c is raised past ~0.4*benefit, giving a cost threshold.
  - P3: Tag clusters turn over cyclically — the dominant tag value shifts repeatedly over time (autocorrelation of population-mean tag decays to near zero within a few hundred generations), confirming the shifting-cluster mechanism rather than a frozen cooperative state.
*vs nearest built:* Nearest is ethnocentrism (Hammond-Axelrod: discrete tags + in/out-group strategy on a grid). Riolo et al. uses CONTINUOUS tags with a tolerance window and NO group strategy or spatial structure — cooperation arises from tag-similarity matching alone, and the lockable claim is the ~0.74 donation rate plus cyclic tag turnover, distinct from ethnocentric in-group bias.

**`optional_public_goods_loners`** — Hauert et al. 2002 — Volunteering as a Red Queen mechanism in public goods games (2002)
*framing:* genuine-agent · *difficulty:* high
*claim:* A loner opt-out option rescues cooperation via rock-paper-scissors-like cycling of cooperators/defectors/loners, avoiding the all-defect collapse of the compulsory game.
*lockable predictions (draft):*
  - P1: Compulsory PGG (no loner option) collapses to near-zero cooperation (cooperator fraction < 0.1 at steady state).
  - P2: Optional PGG with loners sustains positive cooperation (time-averaged cooperator fraction > 0.2) for an intermediate loner payoff 0 < sigma < (r-1).
  - P3: The three strategies cycle: time series of (C,D,L) fractions are oscillatory with the RPS phase ordering (C up -> D up -> L up -> C up), i.e. nonzero rotational/curl signature, not a fixed point.
*vs nearest built:* Nearest are public_goods (compulsory PGG with punishment) and rock_paper_scissors (abstract cyclic dominance). This model is the OPTIONAL PGG whose distinct claim is that voluntary participation (loners) induces RPS-type cycling that rescues cooperation — combining a public-goods payoff with an emergent cyclic attractor neither built model has.

**`fermi_imitation_pd`** — Szabo & Toke 1998 — Evolutionary PD on a square lattice (Fermi rule) (1998)
*framing:* genuine-agent · *difficulty:* high
*claim:* Stochastic Fermi/logit imitation gives a continuous (DP-class) cooperator-extinction transition at a noise-dependent critical temptation b_c.
*lockable predictions (draft):*
  - P1: At fixed noise K, cooperator density rho_C decreases monotonically with temptation b and hits zero at a critical b_c in (1, 2) (e.g. K=0.1 -> b_c ~ 1.0-1.1 region; report the value).
  - P2: The transition is continuous: rho_C -> 0 smoothly as b -> b_c (no discontinuous jump; rho_C < 0.05 within delta b = 0.05 of b_c) rather than a first-order collapse.
  - P3: Selection noise matters: b_c shifts measurably with K (|b_c(K=0.1) - b_c(K=1.0)| > 0.05), confirming the Fermi-rule temperature controls the cooperation transition.
*vs nearest built:* Nearest is nowak_may_pd (DETERMINISTIC best-takes-over spatial PD with a discrete transition). Szabo-Toke uses the STOCHASTIC Fermi/logit update with a tunable temperature K, yielding a continuous (DP-class) phase transition and a noise-dependent critical b_c — a statistical-physics phase-transition claim absent from the deterministic Nowak-May model.

**`coevolving_network_pd`** — Santos, Pacheco & Lenaerts 2006 — Cooperation prevails when individuals adjust their social ties (2006)
*framing:* hybrid (disclose) · *difficulty:* high
*claim:* Degree heterogeneity and active rewiring away from defectors raise cooperation far above the lattice level; faster link-adaptation yields more cooperation.
*lockable predictions (draft):*
  - P1: At fixed temptation b, cooperator fraction on a scale-free (Barabasi-Albert) contact network strictly exceeds that on a degree-matched regular graph (difference > 0.15).
  - P2: With active linking, cooperation increases monotonically with the linking-to-strategy timescale ratio W (cooperator fraction at high W minus at W=0 > 0.2).
  - P3: Heterogeneity broadens the survival range: the critical temptation b_c above which cooperation dies is larger for the scale-free network than for the lattice (b_c shifted up by >= 0.1).
*vs nearest built:* Nearest are nowak_may_pd (FIXED lattice) and barabasi_albert (network GENERATION only, no game). This model puts an evolutionary PD ON TOP of a heterogeneous and/or coevolving network where links and strategies update on coupled timescales — the lockable claim is that topology heterogeneity + active rewiring promote cooperation, which neither the static-lattice game nor the topology-only generator captures.

**`deffuant_amblard_extremists`** — Deffuant, Amblard, Weisbuch & Faure 2002 — Relative agreement with extremists (2002)
*framing:* genuine-agent · *difficulty:* high
*claim:* Under relative-agreement dynamics seeded with fixed extremists, high global uncertainty drives a transition to extreme attractors that capture moderates.
*lockable predictions (draft):*
  - P1: Low uncertainty -> central convergence: for small U (e.g. U<=0.4) moderates converge near 0 and the bimodal-extreme captured fraction stays < 0.2.
  - P2: High uncertainty -> extreme convergence: for large U (e.g. U>=1.2) a majority (> 0.6) of initially-moderate agents end up at one of the extremes (|opinion|>0.8).
  - P3: Single vs double extreme is symmetric-breaking: at intermediate U the outcome is single-extreme (one side captures most moderates) in a substantial fraction (>0.3) of runs rather than always symmetric double-extreme.
*vs nearest built:* Nearest built is Deffuant bounded confidence (symmetric pairwise averaging, fixed threshold, converges to moderate clusters). This variant uses uncertainty-weighted RELATIVE agreement and seeds fixed-position extremists, producing extreme-attractor capture of moderates — a qualitatively different outcome (extremism prevailing) the base Deffuant cannot produce.

### Batch 11 — Random graph generators and structure

**`configuration_model`** — Molloy & Reed 1995 — Critical point for random graphs with a given degree sequence (1995)
*framing:* network-gen (disclose) · *difficulty:* low
*claim:* A giant component exists iff the Molloy-Reed branching ratio kappa=<k^2>/<k> exceeds 2, generalizing the ER <k>=1 Poisson special case.
*lockable predictions (draft):*
  - P1: giant component absent when kappa=<k^2>/<k> < 2 and present when kappa > 2 — largest-component fraction < 0.05 for a degree sequence with kappa=1.5 AND > 0.40 for kappa=3.0 (n=10000, >=10 seeds)
  - P2: the transition crosses exactly at the Molloy-Reed point kappa=2: sweeping kappa over [1.5,3.0], the kappa at which fraction first exceeds 0.05 lies within +/-0.15 of 2.0
  - P3: realized degree distribution matches the target stub sequence — KS distance between sampled and target degree CDF < 0.02 after removing self-loops/multi-edges
*vs nearest built:* Nearest built is erdos_renyi (giant component at <k>=1 for the Poisson case). Configuration model generalizes to ANY degree sequence and shifts the threshold to kappa=<k^2>/<k>=2; ER is the special Poisson case. Tests the heavy-tail-lowers-threshold effect ER cannot.

**`price_citation_model`** — Price 1976 — A general theory of cumulative advantage (citation networks) (1976)
*framing:* network-gen (disclose) · *difficulty:* low
*claim:* Directed growth with attachment proportional to (in-degree+a) gives a tunable power-law in-degree exponent gamma=2+a/m, generalizing BA.
*lockable predictions (draft):*
  - P1: in-degree distribution is power-law with the predicted exponent — for m=3, a=1 the fitted tail exponent gamma in [2.1, 2.6] (theory gamma=2+1/3=2.33), N=50000, >=5 seeds
  - P2: exponent is tunable via a as gamma=2+a/m — gamma(a=1) < gamma(a=3) with both fits separated by >= 0.4 and each within +/-0.3 of 2+a/m
  - P3: directedness matters — out-degree is concentrated near m (CV of out-degree < 0.2) while in-degree is heavy-tailed (max in-degree / mean in-degree >= 10)
*vs nearest built:* Nearest built is barabasi_albert (undirected, gamma fixed near 3, no additive constant). Price's model is DIRECTED (citations are one-way), uses in-degree+a attachment, and the additive a makes gamma TUNABLE in [2,inf) — the original cumulative-advantage model that predates and generalizes BA.

**`maslov_sneppen_rewiring`** — Maslov & Sneppen 2002 — Specificity and stability in protein-network topology (2002)
*framing:* network-gen (disclose) · *difficulty:* low
*claim:* Degree-preserving double-edge-swap rewiring builds an exact-degree null ensemble that reveals significant hub-avoids-hub (disassortative) correlations.
*lockable predictions (draft):*
  - P1: double-edge swaps preserve the degree sequence exactly — every node's degree is unchanged after >= 10*E swaps (max abs degree change = 0 across all nodes)
  - P2: rewiring randomizes degree-degree correlations — for a seeded disassortative network, |assortativity r| after full rewiring < 0.3x its initial value, converging toward the configuration-model baseline
  - P3: the swap ensemble gives a calibrated null with nonzero spread — over >=100 independent rewirings the assortativity has standard deviation > 0 and an input network planted with r<=-0.2 sits >= 2 sigma below the ensemble mean (detected as significantly disassortative)
*vs nearest built:* Nearest built is configuration_model (proposed above) / barabasi_albert, which GENERATE graphs from scratch. Maslov-Sneppen instead RANDOMIZES an existing graph via degree-preserving swaps to build a statistical null model — the canonical tool for testing whether observed degree-degree correlations are significant, not a growth process.

**`holme_kim_clustering`** — Holme & Kim 2002 — Growing scale-free networks with tunable clustering (2002)
*framing:* network-gen (disclose) · *difficulty:* medium
*claim:* A triad-formation step injects high, tunable clustering while preserving the gamma~3 degree tail, decoupling the exponent from clustering (which BA cannot).
*lockable predictions (draft):*
  - P1: clustering rises with triad probability — average clustering C(Pt=0.9) >= 3x C(Pt=0.0) at fixed m=2, N=5000 (BA limit Pt=0 has near-zero C)
  - P2: degree tail stays scale-free and roughly invariant in Pt — fitted gamma in [2.6, 3.4] for both Pt=0.0 and Pt=0.9
  - P3: clustering is monotone non-decreasing in Pt across {0.0,0.3,0.6,0.9} (Spearman correlation = 1.0 over the four points, each averaged over >=5 seeds)
*vs nearest built:* Nearest built is barabasi_albert, which is scale-free but has asymptotically ZERO clustering. Holme-Kim adds a triad-closure step that injects HIGH, TUNABLE clustering while keeping the gamma~3 tail — decoupling the degree exponent from clustering, which BA cannot do.

**`random_geometric_graph`** — Penrose 2003 / Gilbert 1961 — Random geometric graphs (2003)
*framing:* network-gen (disclose) · *difficulty:* medium
*claim:* Proximity-based edges give high clustering (~0.586) and a connectivity threshold pi*n*r^2=ln(n)+c set by isolated vertices, unlike ER.
*lockable predictions (draft):*
  - P1: connectivity threshold scales as ln(n)/n — the smallest r giving a fully connected graph in >= 90% of seeds satisfies pi*n*r^2 within [0.8, 1.5] * ln(n) at n=2000 (>=20 seeds)
  - P2: strong geometric clustering — average clustering coefficient in [0.50, 0.66] for mean degree ~8, i.e. >= 5x an ER graph at the same mean degree
  - P3: giant component appears below the connectivity radius — at mean degree 4.5 the largest component covers > 0.5 of nodes while the graph is NOT yet fully connected
*vs nearest built:* Nearest built is erdos_renyi (edges independent of position, near-zero clustering). RGG embeds nodes in space and links by PROXIMITY, giving high clustering (~0.586) and a connectivity threshold governed by isolated vertices ln(n)/n rather than the giant-component point — a spatial generator ER cannot mimic.

### Batch 12 — Coevolving networks and community structure

**`bianconi_barabasi_fitness`** — Bianconi & Barabasi 2001 — Bose-Einstein condensation in complex networks (2001)
*framing:* network-gen (disclose) · *difficulty:* medium
*claim:* Fitness*degree attachment lets late-but-fit nodes overtake hubs; a top-peaked fitness distribution triggers winner-take-all link condensation.
*lockable predictions (draft):*
  - P1: uniform fitness keeps no condensate — share of links held by the single largest hub stays < 0.10 at N=10000, m=2, fitness ~ U(0,1) (fit-get-rich phase)
  - P2: a condensation-prone fitness distribution (e.g. heavily right-skewed / peaked-at-top) drives winner-take-all — largest hub captures >= 0.40 of all link endpoints, i.e. >= 4x the uniform-fitness case
  - P3: higher fitness wins regardless of arrival order — Spearman correlation between node fitness and final degree >= 0.5 in the uniform-fitness run (late high-fitness nodes overtake early low-fitness ones)
*vs nearest built:* Nearest built is barabasi_albert, where attachment depends on degree ALONE so the oldest node is always richest. Bianconi-Barabasi adds intrinsic node FITNESS, letting late-but-fit nodes overtake hubs and producing a genuine condensation phase transition (Bose-Einstein mapping) absent in pure BA.

**`cont_bouchaud_percolation`** — Cont & Bouchaud 2000 — Herd behavior and aggregate fluctuations (2000)
*framing:* hybrid (disclose) · *difficulty:* medium
*claim:* Random ER coalitions that trade as units produce fat-tailed (excess-kurtosis) returns peaking at the percolation threshold mean degree ~1.
*lockable predictions (draft):*
  - P1: fat tails at criticality — at connectivity c=1 the return distribution has excess kurtosis > 3 (vs ~0 Gaussian) for N>=10^4.
  - P2: tail steepens away from criticality — kurtosis is largest near c=1 and decreases for c well below 1 (single-peaked in c across a 5-point sweep).
  - P3: cluster-size tail exponent — at c=1 the cluster-size distribution follows a power law with exponent in [2.0, 2.7] (mean-field percolation gives 5/2).
*vs nearest built:* Nearest built is erdos_renyi (giant component) and minority_game. erdos_renyi only studies the static graph transition; this COUPLES the ER percolation transition to a TRADING rule so that clusters act collectively, and the lockable object is the heavy-tailed RETURN distribution (kurtosis, tail exponent), not the component size alone. Distinct from minority_game (fixed N adaptive agents, no clustering).

**`sandpile_on_network`** — Goh, Lee, Kahng & Kim 2003 — Sandpile on scale-free networks (2003)
*framing:* hybrid (disclose) · *difficulty:* medium
*claim:* Degree-threshold BTW toppling on a scale-free graph has a non-universal avalanche exponent tau=gamma/(gamma-1), unlike the universal lattice BTW ~1.2.
*lockable predictions (draft):*
  - P1: avalanche-size tail exponent on a Barabasi-Albert substrate (gamma≈3) sits in [1.3, 1.7], measurably LARGER than the same toppling rule run on a 2D lattice (BTW ~1.2)
  - P2: tail exponent varies with topology — tau measured on a scale-free network differs from tau on an Erdos-Renyi random graph of equal mean degree by >= 0.1 (non-universal, geometry-dependent)
  - P3: heavy-tailed avalanches survive on the network — distribution spans >=2 decades AND max avalanche >= 100x median nonzero
*vs nearest built:* Nearest built are btw_sandpile (Euclidean lattice) and barabasi_albert (pure graph growth). This module COMBINES them: it runs the degree-dependent threshold toppling rule (threshold = node degree) on an already-generated scale-free graph, and its load-bearing claim is the NON-universal, gamma-dependent exponent tau=gamma/(gamma-1) — an effect that is impossible on the fixed-coordination lattice of btw_sandpile and absent from the topology-only barabasi_albert.

**`holme_newman_adaptive_voter`** — Holme & Newman 2006 — Coevolution of networks and opinions (2006)
*framing:* hybrid (disclose) · *difficulty:* high
*claim:* Rewiring away from disagreement (rate phi) produces a fragmentation transition at phi_c~0.46: shattered same-opinion components above, one giant component below.
*lockable predictions (draft):*
  - P1: high rewiring fragments the network — at phi=0.95 the largest final same-opinion community covers < 0.2 of nodes (shattered phase), N=3200, G/N=10 opinions
  - P2: low rewiring preserves one giant component — at phi=0.05 the largest final component covers > 0.6 of nodes (consensus/active phase)
  - P3: the transition is sharp near phi_c~0.46 — sweeping phi over [0.0,1.0], the phi at which the largest-component fraction drops below 0.5 lies within +/-0.15 of 0.46
*vs nearest built:* Nearest built is voter_model (fixed graph, opinions only). Holme-Newman makes the TOPOLOGY coevolve: nodes rewire away from disagreement, so structure and opinion feed back. This produces a network-fragmentation phase transition absent from the static-graph voter_model.

**`stochastic_block_model`** — Decelle et al. 2011 — SBM detectability (Holland-Laskey-Leinhardt 1983) (2011)
*framing:* network-gen (disclose) · *difficulty:* high
*claim:* Planted 2-community recovery has a sharp Kesten-Stigum detectability threshold (cin-cout)^2>2(cin+cout), independent of size — a phase transition of inference.
*lockable predictions (draft):*
  - P1: above threshold, planted communities are recoverable — normalized mutual information (or overlap) between a spectral/BP partition and ground truth >= 0.3 when (cin-cout)^2 / [2(cin+cout)] = 2.0 (n=5000, mean degree fixed)
  - P2: below threshold, recovery collapses to chance — NMI < 0.05 when (cin-cout)^2 / [2(cin+cout)] = 0.5
  - P3: the crossover sits at the KS point — sweeping the SNR ratio over [0.3,3.0], the value where NMI first exceeds 0.05 lies within +/-0.5 of ratio=1.0
*vs nearest built:* No community-structured generator is built (erdos_renyi has one homogeneous block; barabasi_albert has no planted groups). SBM is the canonical PLANTED-PARTITION generator and the only candidate exhibiting a detectability phase transition — a property of inference, not just topology.

### Batch 13 — Kinetic-exchange economics and wealth

**`dragulescu_yakovenko_kinetic`** — Dragulescu & Yakovenko 2000 — Statistical mechanics of money (2000)
*framing:* genuine-agent · *difficulty:* low
*claim:* Random money-conserving pairwise exchange drives wealth to a Boltzmann-Gibbs exponential with effective temperature T=<m>, independent of initial conditions.
*lockable predictions (draft):*
  - P1: stationary wealth histogram is exponential — a log-linear fit of P(m) over m in [0, 4<m>] has R^2 > 0.98 and slope = -1/<m> within +-10%.
  - P2: effective temperature equals the per-capita money — fitted decay constant T_fit / (M/N) lies in [0.9, 1.1].
  - P3: convergence is initial-condition-independent — starting all agents equal vs. all money on one agent yields stationary distributions whose fitted T differ by < 5%.
*vs nearest built:* Nearest built is zero_intelligence (Gode-Sunder double auction): that clears trades against private values to test allocative EFFICIENCY. This has no goods/prices/values — agents only swap conserved money at random, and the lockable result is a thermodynamic distributional SHAPE (exponential), not market efficiency. Also distinct from sugarscape, where inequality arises from spatial foraging on a fixed sugar field, not from conservative random transfers.

**`yard_sale_condensation`** — Chakraborti 2002 / Boghosian 2014 — Yard-Sale model (2002)
*framing:* genuine-agent · *difficulty:* low
*claim:* Multiplicative fair-bet exchange condenses all wealth onto one agent (Gini->1); a redistribution tax restores a stable finite-Gini distribution.
*lockable predictions (draft):*
  - P1: condensation — with no redistribution the Gini coefficient rises monotonically and exceeds 0.9 by 10^5 transactions for N=1000.
  - P2: top-share takeover — the single richest agent's share of total wealth exceeds 0.5 in the long run for N=1000 (vs ~0.001 egalitarian start).
  - P3: redistribution restores a stable distribution — adding a per-step wealth-tax chi>0 yields a stationary finite Gini that increases with decreasing chi (monotone chi-Gini relation across a 3-point chi sweep).
*vs nearest built:* Nearest built is dragulescu_yakovenko_kinetic (proposed sibling) and sugarscape. Unlike the additive Dragulescu-Yakovenko model that converges to a stable exponential, the MULTIPLICATIVE fair bet here breaks ergodicity and CONDENSES all wealth onto one agent — opposite qualitative outcome from the same 'random conservative exchange' family, which is exactly the lockable contrast. Distinct from sugarscape (spatial metabolism) which never fully condenses.

**`bouchaud_mezard_wealth`** — Bouchaud & Mezard 2000 — Wealth condensation in a simple economy (2000)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Multiplicative growth plus linear exchange yields a stationary Pareto tail with exponent mu=1+J/sigma^2, condensing below a critical J/sigma^2.
*lockable predictions (draft):*
  - P1: power-law tail — the stationary normalized-wealth distribution has a tail exponent (Hill estimator over the top decile) that is finite and in [1.5, 4] for moderate J/sigma^2.
  - P2: exponent law — increasing J/sigma^2 increases mu monotonically; across a 3-point J sweep at fixed sigma the fitted mu is rank-ordered with J (Spearman = 1).
  - P3: condensation threshold — for small J/sigma^2 the largest-agent share (participation ratio inverse) stays O(1) as N grows, signaling condensation, vs vanishing for large J/sigma^2.
*vs nearest built:* Nearest built is sugarscape (inequality) and the proposed kinetic-exchange models. Unlike conservative kinetic exchange (total money fixed), Bouchaud-Mezard adds MULTIPLICATIVE stochastic GROWTH per agent plus diffusive exchange, producing a tunable POWER-LAW (Pareto) tail with a closed-form exponent — the lockable claim is the exponent law mu = 1 + J/sigma^2, absent from any built model.

**`axtell_firms_zipf`** — Axtell 2001 — Zipf distribution of U.S. firm sizes (2001)
*framing:* genuine-agent · *difficulty:* high
*claim:* Agents forming/joining/leaving firms by effort-allocation choices generate an emergent Zipf firm-size distribution (alpha~1) with skewed growth rates and turnover.
*lockable predictions (draft):*
  - P1: Zipf firm sizes — the stationary firm-size distribution is power-law with a rank-size (or CCDF) exponent alpha in [0.8, 1.3] over at least one decade of sizes.
  - P2: skewed growth rates — the distribution of log firm-size growth rates is leptokurtic (excess kurtosis > 1), not Gaussian.
  - P3: continual turnover — firms are born and die throughout; in steady state the half-life of the top-10 firm identities is finite (membership turns over), not frozen.
*vs nearest built:* Nearest built is sugarscape (emergent inequality) and seceder (group formation). Sugarscape produces a wealth Gini from foraging; seceder produces moving clusters in trait space. Axtell instead has agents endogenously FORM AND DISSOLVE FIRMS by effort-allocation choices, and the lockable target is the ZIPF (alpha~1) firm-SIZE distribution plus growth-rate skew — an industrial-organization power law not produced by any built model.

**`may_complexity_stability`** — May 1972 — Will a large complex system be stable? (1972)
*framing:* hybrid (disclose) · *difficulty:* medium
*claim:* A random S-species community is almost surely stable iff sigma*sqrt(S*C)<1; stability collapses across this critical line, refuting complexity-begets-stability.
*lockable predictions (draft):*
  - P1: the stability transition is at the May line: fraction of random communities that are locally stable crosses 0.5 within +-15% of sigma*sqrt(S*C) = 1.
  - P2: for fixed sigma and C, increasing S decreases stability probability (more complexity is destabilizing): Spearman rho <= -0.9 between S and P(stable) past the critical S.
  - P3: the bulk eigenvalue spread of the random interaction matrix scales as sigma*sqrt(S*C) (circular-law radius), matching the leading eigenvalue's real part to within +-15%.
*vs nearest built:* Nearest built is lotka_volterra (the deterministic 2-species predator-prey ODE producing neutral cycles). May's model is a random-matrix / many-species result: it asks about local stability of an S-species community via eigenvalues of a random Jacobian, yielding a sharp complexity-stability threshold sigma*sqrt(SC)=1. Two species cannot exhibit this transition; the observable is a phase boundary in (S,C,sigma) space, not a limit cycle.

### Batch 14 — Market microstructure and financial stylized facts

**`kim_markowitz_portfolio_insurance`** — Kim & Markowitz 1989 — Investment rules, margin, and market volatility (1989)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Raising the fraction of portfolio-insurers (sell-as-it-falls) vs rebalancers increases volatility super-linearly and can induce crashes — the 1987 mechanism.
*lockable predictions (draft):*
  - P1: monotone volatility increase — across a sweep of insurer fraction f in {0,0.25,0.5,0.75}, realized price-return volatility is monotone non-decreasing in f (Spearman = 1).
  - P2: super-linear / crash regime — at high f (>=0.75) the maximum single-period drawdown is at least 2x that at f=0.
  - P3: rebalancer stabilization — an all-rebalancer market (f=0) has bounded oscillation (volatility below a fixed cap) while all-insurer (f=1) does not (volatility above 2x that cap).
*vs nearest built:* Nearest built is zero_intelligence and minority_game. Those isolate efficiency / side-choosing volatility; Kim-Markowitz isolates the DESTABILIZING feedback of trading-RULE COMPOSITION (portfolio insurers vs rebalancers) on aggregate volatility, the canonical 1987-crash mechanism. The lockable result is a clean A/B/sweep effect of insurer fraction on volatility and drawdown, distinct from any built model's mechanism.

**`lux_marchesi_herding`** — Lux & Marchesi 1999 — Scaling and criticality in a stochastic multi-agent market (1999)
*framing:* genuine-agent · *difficulty:* high
*claim:* Fundamentalists plus switching chartists endogenously generate volatility clustering and a cubic return tail (index ~3) with no exogenous shocks.
*lockable predictions (draft):*
  - P1: inverse-cubic tail — the complementary CDF of absolute returns has a Hill tail index in [2.5, 4.0].
  - P2: volatility clustering — autocorrelation of |returns| stays positive and significant out to lag 50, while raw-return autocorrelation at lag 1 is within +-0.05 of zero.
  - P3: stylized facts vanish under no-switching control — disabling chartist<->fundamentalist switching collapses the tail index above 4 (thin-tailed) and kills volatility-ACF persistence (drops below 0.1 by lag 10).
*vs nearest built:* Nearest built is minority_game (adaptive traders) and zero_intelligence. Minority-game agents pick sides via strategy scores and the metric is volatility vs alpha; Lux-Marchesi instead has agents SWITCH between behavioral types (chartist/fundamentalist) by social herding + price trend, and the lockable claims are emergent FINANCIAL STYLIZED FACTS (cubic tail index, volatility clustering ACF) reproduced without exogenous news — none of which the built models target.

**`brock_hommes_abs`** — Brock & Hommes 1998 — Heterogeneous beliefs and routes to chaos (1998)
*framing:* genuine-agent · *difficulty:* high
*claim:* Fitness-based switching among predictor rules drives a period-doubling route to chaos as the choice intensity beta crosses a critical beta* (positive Lyapunov).
*lockable predictions (draft):*
  - P1: stability loss — for beta below beta* price converges to the fundamental fixed point (|p_t - p*| -> 0); above beta* it does not (sustained oscillation amplitude > tolerance).
  - P2: bifurcation ordering — the asymptotic oscillation amplitude is a monotone non-decreasing function of beta across the sweep just above beta*.
  - P3: positive Lyapunov / chaos — at high beta the largest finite-time Lyapunov exponent of the price series is > 0 (sensitive dependence), vs <= 0 in the stable regime.
*vs nearest built:* Nearest built is el_farol (Arthur inductive expectations) and minority_game. El-Farol locks attendance convergence to ~60; here the lockable phenomenon is a DETERMINISTIC BIFURCATION TO CHAOS in asset price driven by the choice-intensity beta (a fitness-based discrete-choice belief switch), with a Lyapunov-exponent test — a dynamical-systems claim absent from all built models.

**`rosenzweig_macarthur`** — Rosenzweig & MacArthur 1963/1971 — Paradox of enrichment (1971)
*framing:* hybrid (disclose) · *difficulty:* medium
*claim:* Logistic prey plus a Holling-II response undergo a Hopf bifurcation as carrying capacity K rises: a stable equilibrium becomes a limit cycle (enrichment destabilizes).
*lockable predictions (draft):*
  - P1: there is a critical carrying capacity K* such that for K<K* the interior equilibrium is stable (trajectories converge) and for K>K* it is unstable with a stable limit cycle; the measured K* matches the Hopf condition K* = (m*(a+ ...)) within +-15% (analytic boundary computed from the chosen parameter set).
  - P2: enrichment destabilizes: limit-cycle amplitude (peak/trough prey ratio) increases monotonically with K above K* (Spearman rho >= 0.9).
  - P3: below K* the equilibrium is a stable focus (perturbations decay, no sustained oscillation: oscillation amplitude -> 0 within tolerance), distinguishing it from the structurally neutral Lotka-Volterra center.
*vs nearest built:* Nearest built is lotka_volterra, whose classic form has a structurally unstable neutral center (amplitude set by initial conditions, no attracting cycle). Rosenzweig-MacArthur adds prey self-limitation (logistic K) and a Holling-II saturating predator response, which converts the neutral center into a Hopf bifurcation with a genuine attracting limit cycle and the counterintuitive paradox-of-enrichment threshold in K. The lockable observable is a stability-vs-K phase transition that the built LV model structurally cannot have.

**`competitive_lotka_volterra_nspecies`** — MacArthur & Levins 1967 / Gilpin & Ayala 1973 — n-species competitive LV (1967)
*framing:* hybrid (disclose) · *difficulty:* medium
*claim:* Symmetric competition coefficient alpha<1 gives n-species coexistence at N*=K/(1+(n-1)alpha); alpha>1 collapses to competitive exclusion (one survivor).
*lockable predictions (draft):*
  - P1: competitive-exclusion threshold at alpha=1: for symmetric alpha<1 all n species persist (final abundance >0 for each), for alpha>1 exactly one survives; survivor count crosses from n to 1 within +-0.05 of alpha=1.
  - P2: in the coexistence regime the equilibrium abundance matches N* = K/(1+(n-1)alpha) for each species within +-5%.
  - P3: increasing n at fixed alpha<1 lowers per-species equilibrium abundance as 1/(1+(n-1)alpha) (Spearman rho <= -0.9 between n and N*).
*vs nearest built:* Nearest built is lotka_volterra (2-species predator-prey, antagonistic, neutral cycles). This is the n-species COMPETITIVE LV system (all-negative inter-species coefficients, logistic self-limitation) whose canonical result is a competitive-exclusion / limiting-similarity threshold and a closed-form coexistence equilibrium across n species — a fundamentally different interaction sign-structure and a different lockable observable (survivor count vs alpha) than predator-prey cycling.

### Batch 15 — Reaction-diffusion and growth morphogenesis

**`dla_witten_sander`** — Witten & Sander 1981 — Diffusion-limited aggregation (1981)
*framing:* genuine-agent · *difficulty:* low
*claim:* Sequentially released sticking random walkers grow a self-similar fractal cluster with mass dimension D~1.71 via Laplacian tip screening.
*lockable predictions (draft):*
  - P1: A 2D DLA cluster of >= 20000 particles has fractal dimension D = 1.71 +/- 0.06, fitted from log M vs log R_g over at least 1.5 decades of R_g.
  - P2: The cluster is ramified/branched not compact: its occupied-mass fraction inside the convex hull (or bounding radius) decreases as cluster size grows, scaling as N^{(D-2)/D} and falling below 0.3 by N=20000 (D < 2).
  - P3: Growth is tip-dominated (screening): the radial density of sticking events is strongly peaked near the cluster periphery, with the outer 20% radial shell receiving > 60% of new particles, distinguishing DLA from compact (Eden) growth.
*vs nearest built:* Nearest built is btw_sandpile (self-organized criticality via toppling, an SOC exponent claim) and bak_sneppen. DLA is a growth/aggregation process driven by autonomous random-walker particles whose lockable quantity is a static fractal mass dimension D~1.71 from Laplacian screening, not an avalanche/size-distribution exponent. No diffusing-particle aggregation model exists in the suite.

**`eden_growth`** — Eden 1961 / Jullien & Botet 1985 — Two-dimensional growth process (1961)
*framing:* CA (disclose) · *difficulty:* low
*claim:* Random perimeter addition gives a compact cluster (D=2) whose interface is KPZ-rough: roughness exponent alpha=1/2, growth exponent beta=1/3.
*lockable predictions (draft):*
  - P1: An Eden cluster is compact: occupied-mass fraction inside its bounding radius stays > 0.85 and the radius-of-gyration mass dimension D = 2.0 +/- 0.05 (sharply distinct from DLA's D~1.71).
  - P2: Growing from a flat seed line of width L, the saturated interface width scales as w_sat ~ L^alpha with alpha = 0.50 +/- 0.10 (KPZ 1+1 roughness exponent).
  - P3: Before saturation the interface width grows as w(t) ~ t^beta with beta = 0.33 +/- 0.08 (KPZ growth exponent), measured over at least one decade in t.
*vs nearest built:* Nearest built is forest_fire (percolation/SOC cluster burning) and game_of_life. Eden growth is a stochastic compact-cluster growth model whose lockable quantities are the compact bulk dimension D=2 and the KPZ interface exponents alpha=1/2, beta=1/3 — interface-roughness universality, absent from the suite. It is the deliberate compact contrast to dla_witten_sander (same proposal batch, opposite morphology).

**`gray_scott_reaction_diffusion`** — Pearson 1993 / Gray & Scott 1984 — Complex patterns in a simple system (1993)
*framing:* CA (disclose) · *difficulty:* medium
*claim:* The two-species Gray-Scott system partitions the (F,k) plane into spots, stripes and trivial collapse — a quantitative Pearson morphology atlas.
*lockable predictions (draft):*
  - P1: At F=0.030, k=0.062 (Du=0.16,Dv=0.08 on 256x256, dt=1) a seed perturbation undergoes self-replication: number of distinct spots grows monotonically and saturates at >= 30 spots, never collapsing to the trivial U=1,V=0 state.
  - P2: At F=0.022, k=0.051 the steady state is labyrinthine stripes: final V-field has stripe-like connected components with mean width 4-8 cells and stripe area fraction 0.35-0.55, distinct from isolated spots (component count grows then plateaus, components are elongated with aspect ratio > 3).
  - P3: At F=0.018, k=0.070 (outside the active wedge) any localized seed decays: total V mass monotonically decreases to < 1% of initial within 5000 steps (homogeneous trivial fixed point).
*vs nearest built:* Nearest built model is game_of_life (a discrete totalistic CA on a binary grid). Gray-Scott is a continuous-state two-field reaction-diffusion PDE whose patterns arise from a Turing-type diffusive instability (Du != Dv), not from discrete birth/death rules; the lockable claim is a parameter-plane morphology map, not a still-life/oscillator census.

**`turing_pattern_fhn`** — Turing 1952 — The chemical basis of morphogenesis (activator-inhibitor) (1952)
*framing:* CA (disclose) · *difficulty:* medium
*claim:* Diffusion destabilizes a stable homogeneous state only above a critical inhibitor/activator diffusion ratio d_c, selecting a finite wavelength k* set by the dispersion relation.
*lockable predictions (draft):*
  - P1: For diffusion ratio d below the linear-stability threshold d_c the homogeneous state persists (spatial variance stays < 1% of mean); for d above d_c spatial variance grows and saturates to a patterned state, with the measured onset matching the analytic d_c within +/- 10%.
  - P2: Above onset the emergent pattern has a dominant wavelength: the radially-averaged 2D power spectrum peaks at a nonzero wavenumber k* matching the fastest-growing mode of the dispersion relation within +/- 15%, and k* is insensitive (< 10% change) to a 2x change in domain size (intrinsic, not boundary-set).
  - P3: Pattern wavelength scales as sqrt(D_activator): doubling D_activator at fixed ratio d increases measured k*^-1 by a factor 1.41 +/- 0.15.
*vs nearest built:* Nearest built is kuramoto (phase-oscillator synchronization with no space). Turing/FHN is spatial morphogenesis where the instability is diffusion-driven and the lockable quantity is the critical diffusion ratio and the linearly-selected wavelength k*, a fundamentally different (Turing-bifurcation) mechanism than phase locking. Also distinct from gray_scott: here the claim is the analytic dispersion-relation onset and wavelength selection, not Pearson's empirical (F,k) morphology atlas.

**`keller_segel_chemotaxis`** — Keller & Segel 1970 — Initiation of slime mold aggregation (1970)
*framing:* hybrid (disclose) · *difficulty:* medium
*claim:* Agents that secrete and climb a diffusing attractant aggregate once chemotactic sensitivity exceeds a critical threshold; diffusion re-homogenizes below it.
*lockable predictions (draft):*
  - P1 aggregation threshold: a clustering index (e.g. peak-to-mean density, or Moran's I of the cell field) stays near the uniform baseline (<1.5× baseline) below a critical chemotactic coupling χ_c and exceeds it (>3× baseline) above χ_c.
  - P2 monotone aggregation: the clustering index is monotone non-decreasing in χ across the swept grid.
  - P3 diffusion stabilizes: at fixed χ above threshold, increasing attractant diffusion D back above a value re-homogenizes the field (clustering index returns below 1.5× baseline), confirming the D-vs-χ competition rather than a one-sided effect.
*vs nearest built:* Nearest built models are sugarscape_inequality (agents moving on a resource field) and ant_foraging (pheromone fields). It differs from ant_foraging because there is NO foraging task, no nest, and no trail-following toward food — agents secrete the very field they climb, producing a self-amplifying aggregation INSTABILITY with a critical sensitivity, which is the lockable result. It differs from sugarscape because the field is endogenous (cell-secreted, diffusing, degrading) rather than an exogenous sugar landscape, and the locked quantity is an aggregation threshold, not a wealth/Gini distribution.

### Batch 16 — Excitable media and driven cellular automata

**`greenberg_hastings_excitable`** — Greenberg & Hastings 1978 — Discrete excitable media (1978)
*framing:* CA (disclose) · *difficulty:* low
*claim:* The 3-state excitable CA sustains rotating spirals with a fixed rotation period; wavefronts annihilate on collision and re-entry needs a critical domain size.
*lockable predictions (draft):*
  - P1: Seeded with a broken wavefront, the medium develops a rotating spiral whose tip executes periodic rotation with a fixed period T (period equals total cycle length = excited + refractory states) that is stable to within +/- 1 step over >= 20 rotations.
  - P2: Two colliding excitation wavefronts annihilate (no passing-through): after a head-on collision the total excited-cell count drops to 0 at the collision front within one refractory period, never producing transmitted waves.
  - P3: Sustained spiral re-entry requires the domain perimeter to exceed the wave's refractory wavelength: below a critical linear size L_c (proportional to refractory period n) all activity dies within < 5 cycles, while above L_c spirals persist > 100 cycles; L_c scales linearly with n (+/- 20%).
*vs nearest built:* Nearest built is game_of_life (binary totalistic CA) and forest_fire (which has a transient burn but no rotating re-entry). Greenberg-Hastings is a 3-state excitable CA whose lockable behaviors — annihilating wavefronts, fixed spiral rotation period, and a refractory-set critical size for sustained re-entry — are excitable-media dynamics with no analog in the built models.

**`cyclic_cellular_automaton`** — Fisch, Gravner & Griffeath 1991 — Cyclic cellular automata in 2D (1991)
*framing:* CA (disclose) · *difficulty:* medium
*claim:* n-color neighbor-matched advancement self-organizes into rotating spirals for small n but fixates into static debris above a critical color count n_c.
*lockable predictions (draft):*
  - P1: For n=8 colors (Moore neighborhood, threshold 1) on a 256x256 torus from random IC, the system enters the spiral phase: persistent rotating spiral cores form and the fraction of cells changing color per step settles to a nonzero plateau (> 0.2) rather than freezing.
  - P2: For n above the critical color count (e.g. n=16+) the dynamics fixate: the fraction of cells changing color per step decays to < 0.01 within the run (jammed/debris phase), giving a sharp spiral-to-fixation transition as n crosses n_c.
  - P3: In the spiral phase the demon/cycle period of an established spiral core equals exactly n (it takes n steps to complete one color cycle), verifiable to within +/- 0 steps for a tracked core.
*vs nearest built:* Nearest built is rock_paper_scissors (3-strategy cyclic-dominance spatial game producing spirals) and game_of_life. The cyclic CA differs in that cells are NOT playing a payoff game — they deterministically advance through n>3 cyclic color states by neighbor-matching, and the lockable claim is a spiral-vs-fixation phase transition in the number of colors n (a count-of-states critical parameter), absent from the RPS 3-species ESS claim.

**`biham_middleton_levine`** — Biham, Middleton & Levine 1992 — Self-organization and a dynamical transition in traffic (1992)
*framing:* CA (disclose) · *difficulty:* low
*claim:* The 2D two-species traffic CA shows a sharp density-driven free-flow-to-gridlock transition (velocity 1->0) with diagonal jam bands near rho_c~0.3-0.4.
*lockable predictions (draft):*
  - P1 (sharp transition): asymptotic average velocity drops from ~1 (free-flow) to ~0 (jam) across a narrow density window; the transition density rho_c lies in [0.30, 0.40].
  - P2 (order of phases): for rho well below rho_c, steady-state mean velocity = 1.0 exactly (perfect free flow); for rho well above rho_c, steady-state mean velocity = 0.0 exactly (full gridlock).
  - P3 (intermediate structure): near rho_c diagonal jam bands form — the velocity-vs-density curve is sharply non-linear (a near-step), not a smooth gradual decline.
*vs nearest built:* Nearest built is nagel_schreckenberg (1D ring, velocity 0..5, free-flow vs congested fundamental diagram, no true phase transition). BML is intrinsically 2D with two interleaved species moving on alternating ticks; its signature is a genuine sharp jamming PHASE TRANSITION (velocity 1→0) absent from the 1D NaSch fundamental diagram.

**`tasep_open_boundary`** — Derrida, Evans, Hakim & Pasquier 1993 — Exact TASEP with open boundaries (1993)
*framing:* CA (disclose) · *difficulty:* medium
*claim:* Injection/extraction rates set three phases (low-density, high-density, maximal-current J=1/4) with an exactly known phase diagram and coexistence line alpha=beta<1/2.
*lockable predictions (draft):*
  - P1 (maximal-current plateau): for alpha,beta > 0.5 steady-state current J = 0.25 +/- 0.02, independent of alpha,beta.
  - P2 (low-density phase): for alpha < 0.5 and alpha < beta, J ≈ alpha(1-alpha) and bulk density ≈ alpha (match within +/-0.03).
  - P3 (coexistence line): on alpha=beta<0.5 a linear density profile (shock) appears, and crossing it flips the bulk density from ~alpha to ~1-beta.
*vs nearest built:* Nearest built is nagel_schreckenberg (closed ring, vmax=5, no boundary-driven phases). TASEP is the minimal hopping-exclusion process (vmax=1) with OPEN boundaries; its hallmark is a boundary-induced three-phase diagram with an exactly known current 1/4 — a different, analytically exact target NaSch's ring never reaches.

**`ant_trail_bidirectional`** — Chowdhury et al. 2002 — A cellular-automaton model of ant-trail flow (2002)
*framing:* CA (disclose) · *difficulty:* medium
*claim:* Pheromone-modulated hopping gives an anomalous fundamental diagram: a velocity plateau and a right-shifted flow peak that revert to NaSch as evaporation->1.
*lockable predictions (draft):*
  - P1 (loose clusters / plateau): mean velocity is roughly flat (varies <20%) across an intermediate density band rather than declining steadily as in NaSch.
  - P2 (asymmetric fundamental diagram): the density of maximum flow is shifted to rho > 0.5 (skewed right), unlike the symmetric/low-rho NaSch peak.
  - P3 (pheromone control): increasing evaporation rate f toward 1 recovers NaSch-like behavior (peak moves back toward rho~0.5 and the velocity plateau disappears).
*vs nearest built:* Nearest built are nagel_schreckenberg (no pheromone; symmetric fundamental diagram) and ant_foraging (2D stigmergy, not a 1D fundamental-diagram model). This couples a NaSch-like exclusion process to an evaporating pheromone field, yielding a qualitatively different ANOMALOUS fundamental diagram (velocity plateau, right-shifted flow peak).

### Batch 17 — Self-organized criticality variants

**`manna_sandpile`** — Manna 1991 — Two-state model of self-organized criticality (1991)
*framing:* CA (disclose) · *difficulty:* low
*claim:* Stochastic two-neighbor toppling defines the Manna universality class with avalanche exponent tau~1.27, distinct from deterministic BTW.
*lockable predictions (draft):*
  - P1: discrete-MLE avalanche-size tail exponent tau in [1.20, 1.40] (Manna 2D), distinct from a pure BTW fit on the same grid
  - P2: heavy-tailed not exponential — size distribution spans >=2 decades AND max avalanche >= 100x median nonzero
  - P3: stochastic toppling gives finite stationary activity density rho* > 0 at criticality with rho* differing from the BTW-conserved height (mean occupancy in [0.6, 0.95] for the two-state rule)
*vs nearest built:* Nearest built is btw_sandpile (deterministic, conservative, height>=4 splits to 4 fixed neighbours). Manna differs by RANDOM redistribution: a toppling site sends its 2 grains to two RANDOMLY chosen neighbours, defining a separate (Manna/C-DP) universality class with a different tau and stochastic — not deterministic — dynamics. Also distinct from olami_feder_christensen (non-conservative continuous forces).

**`abelian_directed_sandpile`** — Dhar & Ramaswamy 1989 — Exactly solved directed abelian sandpile (1989)
*framing:* CA (disclose) · *difficulty:* low
*claim:* Anisotropic downward-only toppling is exactly solvable with tau=4/3 and an avalanche geometry biased along the drive direction.
*lockable predictions (draft):*
  - P1: avalanche-size tail exponent tau in [1.2, 1.5] consistent with the EXACT value 4/3≈1.333 (tighter, theory-pinned bar than the looser BTW prior)
  - P2: anisotropic avalanche geometry — avalanches are directionally biased: mean longitudinal extent exceeds mean transverse extent by >= 2x (directed propagation, unlike isotropic BTW)
  - P3: heavy-tailed sizes span >=2 decades AND max avalanche >= 100x median nonzero, matching the exactly known scaling
*vs nearest built:* Nearest built is btw_sandpile (undirected, isotropic, tau≈1.2). The directed/abelian variant differs by an ANISOTROPIC toppling rule (grains pass only 'downward' to a preferred subset of neighbours), which makes the model EXACTLY solvable with a distinct, theory-fixed exponent tau=4/3 and a measurable directional avalanche anisotropy that isotropic BTW cannot exhibit.

**`oslo_ricepile`** — Christensen et al. 1996 — Oslo rice-pile model (1996)
*framing:* CA (disclose) · *difficulty:* medium
*claim:* Stochastic per-site critical slopes make a 1D pile genuinely critical (tau~1.55) where deterministic 1D BTW is trivial; cutoff scales with system size.
*lockable predictions (draft):*
  - P1: discrete-MLE avalanche-size tail exponent tau in [1.4, 1.7] (Oslo 1D)
  - P2: genuinely critical in 1D — size distribution spans >=2 decades AND max avalanche >= 100x median nonzero (whereas a 1D deterministic BTW pile is NOT critical / trivial)
  - P3: cutoff scales with system size — mean avalanche size grows monotonically with L across L in {32,64,128,256} (larger L => larger <s>)
*vs nearest built:* Nearest built is btw_sandpile (2D deterministic, fixed threshold). Oslo differs by being 1D with STOCHASTIC per-site critical slopes z_c randomly reset in {1,2} after each toppling — this is what makes 1D non-trivially critical (deterministic 1D BTW is not). Different universality class and exponent (~1.55) from BTW (~1.2) and from forest_fire.

**`sneppen_depinning`** — Sneppen 1992 — Self-organized pinning and interface growth (1992)
*framing:* CA (disclose) · *difficulty:* medium
*claim:* Extremal advancement of the minimum-pinning site grows a self-affine interface (roughness chi~0.63) with scale-free avalanches in a distinct depinning class.
*lockable predictions (draft):*
  - P1: self-affine interface — saturated width W(L)~L^chi with measured roughness exponent chi in [0.5, 0.75] (Sneppen depinning class)
  - P2: scale-free activity — avalanche/jump-size distribution between pinning configurations is heavy-tailed: spans >=2 decades AND max >= 100x median
  - P3: faceted/anticorrelated growth — interface-height increments are spatially anticorrelated (nearest-neighbour height-difference correlation < 0), distinguishing it from uncorrelated random deposition
*vs nearest built:* Nearest built is bak_sneppen (the SAME author's extremal-update idea on a fitness ring) and forest_fire. Sneppen depinning differs by acting on an INTERFACE HEIGHT profile in a quenched random medium: the extremal rule advances the site of minimum pinning force and updates a spatial height field, yielding a measurable roughness exponent chi (a geometric/self-affine observable) — Bak-Sneppen has no spatial height field or roughness exponent, only a fitness ring.

**`burridge_knopoff`** — Carlson & Langer 1989 (after Burridge & Knopoff 1967) — Mechanical earthquake fault (1989)
*framing:* genuine-agent · *difficulty:* high
*claim:* A spring-block stick-slip fault with inertia and velocity-weakening friction gives Gutenberg-Richter scaling plus a characteristic large-event bump.
*lockable predictions (draft):*
  - P1: small-event moment distribution is power-law — discrete/continuous-MLE slip-size exponent in [1.5, 2.5] over the scaling region (Gutenberg-Richter b≈1 region)
  - P2: heavy-tailed slip events span >=2 decades in moment AND max slip >= 100x median, NOT exponential
  - P3: stiffness/velocity-weakening controls scaling — increasing the spring stiffness ratio l reduces the power-law range and sharpens the large-event peak (mean event size decreases as l increases)
*vs nearest built:* Nearest built is olami_feder_christensen (which is itself a CA caricature of B-K). Burridge-Knopoff differs by being a genuine MECHANICAL agent model: each block carries continuous position/velocity STATE and integrates Newtonian equations of motion with a velocity-weakening friction law and inertia — not a discrete cellular threshold-redistribution rule. Inertia and the friction nonlinearity (absent in OFC) drive the characteristic-earthquake bump.

### Batch 18 — Collective animal motion

**`buhl_locust_marching`** — Buhl et al. 2006 — From disorder to order in marching locusts (2006)
*framing:* genuine-agent · *difficulty:* low
*claim:* A 1D ring-arena alignment model shows a density-driven onset of collective marching with spontaneous global direction reversals near threshold.
*lockable predictions (draft):*
  - P1 density threshold: mean absolute alignment |⟨v⟩| is low (<0.3) at low density and high (>0.7) at high density, with a monotone increase in density — a clear order/disorder crossover.
  - P2 intermittent switching near threshold: at intermediate density the sign of the net direction flips at least once over a long run (switching rate > 0), whereas at high density it never flips (rate ≈ 0).
  - P3 alignment is monotone non-decreasing in density across the swept grid (tolerance 0.05).
*vs nearest built:* Nearest built model is vicsek_flocking. Vicsek's standard locked sweep is over NOISE η at fixed density on a 2D torus and locks a noise-driven transition; it does not lock a DENSITY threshold nor the 1D intermittent direction-switching that is the empirical signature of Buhl's marching locusts. This model is the 1D (ring-arena) Czirok variant with the control parameter being DENSITY and the lockable signatures being the density threshold plus spontaneous global-direction reversals near criticality — neither is the metric vicsek_flocking reproduces.

**`mirollo_strogatz_fireflies`** — Mirollo & Strogatz 1990 — Synchronization of pulse-coupled oscillators (1990)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Integrate-and-fire oscillators with a concave charging curve and pulsatile coupling synchronize for almost all initial conditions and all N, with no coupling threshold.
*lockable predictions (draft):*
  - P1 universal sync: starting from random phases, the fraction of oscillators firing within one absorption window reaches 1.0 (full sync) for ≥ 95% of random seeds at N=100, ε=0.1, concave curve.
  - P2 coupling speeds sync: median cycles-to-sync is strictly smaller at ε=0.2 than at ε=0.05 (monotone decrease with ε).
  - P3 concavity is necessary: with a LINEAR (non-concave) charging curve the same protocol fails to reach full sync for most seeds (sync fraction < 0.5), confirming concavity — not mere pulse coupling — drives the result.
*vs nearest built:* Nearest built model is kuramoto. Kuramoto uses CONTINUOUS sinusoidal phase coupling and has a finite critical coupling K_c = 2/(π g(0)) below which the system is incoherent. Mirollo-Strogatz uses DISCRETE integrate-and-fire PULSE coupling with state resets and an absorption mechanism, syncs for almost-all initial conditions with NO finite coupling threshold, and crucially depends on curve CONCAVITY. The lockable phenomena (measure-1 universal sync, concavity-necessity, pulse-driven absorption) are absent from the kuramoto module, which has no firing/reset events and no concavity dependence.

**`couzin_zonal_model`** — Couzin et al. 2002 — Collective memory and spatial sorting in animal groups (2002)
*framing:* genuine-agent · *difficulty:* medium
*claim:* A three-zone self-propelled model produces four discrete states (swarm/mill/dynamic/parallel) as the orientation-zone width grows, with hysteresis between them.
*lockable predictions (draft):*
  - P1 mill regime exists: for a narrow orientation zone (small Δzoo) the group polarization p stays low (p < 0.35) while normalized angular momentum m is high (m > 0.65), i.e. a torus/mill — distinct from a polarized flock.
  - P2 parallel regime: for a wide orientation zone (large Δzoo) polarization is high (p > 0.9) and angular momentum collapses (m < 0.2).
  - P3 hysteresis: sweeping Δzoo up vs down, the Δzoo value at the swarm->polarized switch differs from the polarized->swarm switch by a finite gap (≥ 1 model length-unit), so the state is history-dependent.
*vs nearest built:* Nearest built model is vicsek_flocking (and boids). Vicsek is a single alignment rule on a torus with scalar noise and yields only an order/disorder transition (one threshold, one order parameter phi); boids is a force-balance with no zone-width control parameter. Couzin's defining result — the milling/torus state and bistable HYSTERESIS between collective states as a single zone-width parameter varies — cannot appear in Vicsek (no mill, no hysteresis) and is not the metric boids locks. The lockable quantity here is the (polarization, angular-momentum) phase portrait and the hysteresis gap, neither of which exists in vicsek_flocking.

**`couzin_informed_leadership`** — Couzin et al. 2005 — Effective leadership and decision-making on the move (2005)
*framing:* genuine-agent · *difficulty:* medium
*claim:* A vanishing informed fraction guides a large group (required fraction ~1/N); two informed subgroups average for small angular differences and pick the majority for large.
*lockable predictions (draft):*
  - P1 few leaders suffice: at fixed N=100, group directional accuracy exceeds 0.9 (cos of error angle) with an informed fraction p ≤ 0.10.
  - P2 size effect: the informed fraction needed to reach accuracy 0.9 is strictly smaller for N=200 than for N=30 (monotone decrease with N).
  - P3 majority vs averaging: with two equal-size informed subgroups, group heading averages the two preferences when the angle between them is small (<≈60°) but commits to one (majority/symmetry-break) when the angle is large (>≈120°).
*vs nearest built:* Nearest built models are couzin_zonal_model (same zonal substrate) and the opinion-dynamics models galam_majority / majority_vote. It differs from couzin_zonal_model by adding GOAL-DIRECTED informed minorities and locking a leadership-fraction-vs-accuracy curve (a 1/N leader-economy law), not a milling/hysteresis phase portrait. It differs from galam/majority_vote because consensus emerges from continuous spatial motion and heading vectors, not discrete spin/vote flips on a lattice — the order parameter is geometric heading accuracy, and the lockable result is the leader-fraction threshold and its N-scaling.

**`huth_wissel_fish_schooling`** — Huth & Wissel 1992 — The simulation of the movement of fish schools (1992)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Averaging neighbor directions yields markedly higher polarization and tighter cohesion than a decide-on-one-neighbor rule, both with the same zonal forces.
*lockable predictions (draft):*
  - P1 averaging beats decision on polarization: mean school polarization p_avg under the averaging rule exceeds p_dec under the decision rule by ≥ 0.15 at matched parameters.
  - P2 cohesion: nearest-neighbor distance is more tightly regulated under averaging (coefficient of variation of NND smaller than under the decision rule).
  - P3 both rules school: both rules still produce a polarized school (p > 0.5) rather than disorder, so the effect is a quantitative averaging-advantage, not averaging-vs-no-schooling.
*vs nearest built:* Nearest built models are boids and vicsek_flocking. Boids locks alignment-ON vs alignment-OFF (a rule-presence A/B) and vicsek locks a noise transition. Huth-Wissel's locked contrast is an entirely different A/B: AVERAGING-many-neighbors vs DECIDING-on-one-neighbor as the integration rule, both with the same zonal forces present — a mechanism comparison boids does not contain (boids always averages). The lockable result is the polarization gap between two information-integration rules, not the presence/absence of an alignment force.

### Batch 19 — Stigmergy, swarm decisions and pedestrian crowds

**`deneubourg_corpse_clustering`** — Deneubourg et al. 1991 — The dynamics of collective sorting (1991)
*framing:* genuine-agent · *difficulty:* low
*claim:* Density-dependent pick-up/drop rules coarsen scattered items into a few growing clusters with no template; cluster count decays where a density-independent control stays dispersed.
*lockable predictions (draft):*
  - P1 clustering vs random: after the run, the number of distinct item clusters is far below the no-density-bias control (≤ 50% of the control cluster count) and mean cluster size is correspondingly larger.
  - P2 coarsening: cluster count is monotone non-increasing over time after an initial transient (it never net-increases), and mean cluster size grows.
  - P3 feedback necessity: with density-INDEPENDENT pick/drop probabilities (control), items stay dispersed (cluster-size index near random baseline), confirming the density feedback — not mere random walk — drives sorting.
*vs nearest built:* Nearest built models are ant_foraging and schelling_segregation. It differs from ant_foraging because there is NO pheromone field, no food source, and no nest — clustering is driven purely by local-density-dependent pick-up/drop rules on inert items (brood sorting), and the lockable result is cluster-count coarsening, not trail formation. It differs from schelling because items are PASSIVE (carried by separate ant agents) with probabilistic density-feedback rules rather than agents relocating by a satisfaction threshold; the order parameter is cluster count/size over time, not a segregation index.

**`floor_field_ca_evacuation`** — Kirchner & Schadschneider 2002 — Bionics-inspired evacuation CA with floor fields (2002)
*framing:* CA (disclose) · *difficulty:* medium
*claim:* A probabilistic static+dynamic floor-field CA reproduces faster-is-slower: over-greedy static coupling clogs the door, and dynamic-field coupling induces herding.
*lockable predictions (draft):*
  - P1 (faster-is-slower in a CA): total evacuation time as a function of static-field coupling k_S is non-monotonic with an interior minimum; T at very large k_S exceeds T at the optimal k_S by >=10%.
  - P2 (herding via dynamic field): increasing dynamic-field coupling k_D concentrates outflow through fewer cells — exit-usage entropy decreases monotonically with k_D.
  - P3 (jamming transition): at fixed door width, evacuation time per agent grows super-linearly once initial density exceeds ~0.6 occupancy.
*vs nearest built:* Nearest built are game_of_life and forest_fire (synchronous CA) and nagel_schreckenberg (1D driven CA). This is a 2D pedestrian-evacuation CA whose transition rule is a probabilistic floor-field (static distance field + diffusing/decaying dynamic trail), a fundamentally different rule class and observable (egress time vs door width) than any built CA.

**`honeybee_quorum_consensus`** — List, Elsholtz & Seeley 2009 — Independence and interdependence in collective decisions (2009)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Cross-inhibition between committed scouts breaks deadlock between equal sites and selects the higher-quality site; without it equal sites stall indefinitely.
*lockable predictions (draft):*
  - P1 quality discrimination: with two unequal sites, the probability the swarm commits to the BETTER site exceeds 0.9 within the run horizon.
  - P2 deadlock without inhibition: with two EQUAL sites and cross-inhibition OFF, the swarm fails to commit (neither site reaches the quorum fraction, e.g. both < 0.7) for most seeds.
  - P3 inhibition breaks deadlock: with two equal sites and cross-inhibition ON above a critical strength, exactly one site reaches quorum (>0.8) — symmetry is broken — for ≥ 90% of seeds.
*vs nearest built:* Nearest built models are galam_majority / majority_vote / naming_game (consensus dynamics) and minority_game. Those are lattice/well-mixed opinion or coordination games with no notion of OPTION QUALITY or a stop-signal. Honeybee quorum locks two things absent from all of them: (i) accuracy of choosing the higher-QUALITY option, and (ii) cross-inhibition as the deadlock-breaking mechanism with a critical inhibition strength. The lockable results are decision accuracy and the inhibition-driven symmetry break, not bare majority consensus.

**`helbing_lane_formation`** — Helbing & Molnar 1995 — Social force model for pedestrian dynamics (1995)
*framing:* genuine-agent · *difficulty:* high
*claim:* Counter-flowing pedestrians self-organize into segregated unidirectional lanes, raising throughput; lane count grows with corridor width/density.
*lockable predictions (draft):*
  - P1 (lane segregation): a lane-order parameter (local left/right directional sorting, 0=mixed,1=fully sorted) rises from ~0 at start to >=0.6 in steady state for moderate density.
  - P2 (throughput gain): steady-state crossing flux per pedestrian is >=20% higher after lanes form than during the initial mixed transient at the same density.
  - P3 (density dependence): the number of self-organized lanes increases (weakly) with corridor width / density rather than staying fixed at 1.
*vs nearest built:* Nearest built is boids/vicsek (alignment flocking, no opposing goals). Here two populations have OPPOSING goal directions and physical repulsion; the emergent observable is spontaneous spatial SEGREGATION into lanes (a counter-flow effect), absent from any single-direction flocking model.

**`helbing_escape_panic`** — Helbing, Farkas & Vicsek 2000 — Simulating dynamical features of escape panic (2000)
*framing:* genuine-agent · *difficulty:* high
*claim:* Faster-is-slower: above a critical desired speed, higher speed increases egress time through a single exit, with intermittent clogging and door arching.
*lockable predictions (draft):*
  - P1 (faster-is-slower): egress time T(v_d) is non-monotonic — it has an interior minimum, so T at a high v_d (e.g. 5 m/s) is strictly greater than T at the optimal v_d (~1.5 m/s) by >=15%.
  - P2 (clogging/arching): at high v_d the instantaneous outflow at the door is intermittent (coefficient of variation of inter-exit gaps >= 0.5), vs near-regular outflow (CV <= 0.2) at low v_d.
  - P3 (density buildup): time-averaged crowd density just upstream of the exit increases monotonically with v_d and exceeds ~5 persons/m^2 at high v_d.
*vs nearest built:* Nearest built is vicsek_flocking (and boids): Vicsek is alignment-only self-propelled particles with no goal, no body exclusion, no walls. Helbing adds a Newtonian social-force law (exponential repulsion + body compression + sliding friction) and a goal/exit, producing the faster-is-slower congestion effect Vicsek cannot show.

### Batch 20 — Eco-evolutionary assembly and life-history

**`penna_aging`** — Penna 1995 — A bit-string model for biological aging (1995)
*framing:* genuine-agent · *difficulty:* medium
*claim:* An age-indexed deleterious-mutation genome reproduces the Gompertz exponential mortality rise and a senescence cliff just past the reproduction age; lifespan grows with the death threshold.
*lockable predictions (draft):*
  - P1: log-mortality is approximately linear in age over the adult span (Gompertz), with R^2 >= 0.9 for the exponential fit across ages between R and the catastrophe age.
  - P2: there is a catastrophe/senescence cliff: survivorship S(age) stays high (>0.5 of the post-maturation cohort) up to age ~R then falls to <0.1 within a few timesteps after R, i.e. almost no individuals survive far beyond R.
  - P3: raising the deleterious-mutation threshold T monotonically increases mean lifespan / mean population age (Spearman rho >= 0.9 across a T grid).
*vs nearest built:* Nearest built is moran_process / wright_fisher (allele fixation under drift+selection in a fixed-size haploid pool). Penna is fundamentally different: each agent carries an age-indexed genome bit-string of inherited deleterious mutations and an explicit age, so the observable is an age-structured mortality/survivorship curve (Gompertz exponent, senescence cliff), not an allele-frequency fixation probability. No age structure or genome bit-string exists in any built model.

**`linear_threshold_influence`** — Kempe, Kleinberg & Tardos 2003 — Linear Threshold influence maximization (2003)
*framing:* genuine-agent · *difficulty:* medium
*claim:* Weighted-threshold activation is monotone submodular (greedy gives 1-1/e), and the greedy-optimal seed set diverges from the Independent Cascade optimum on the same graph.
*lockable predictions (draft):*
  - P1: Submodular marginal gains: greedy marginal gain non-increasing in seed index k (within noise).
  - P2: Random-threshold criticality: averaged over uniform thresholds, final activated fraction increases monotonically with normalized edge weight / seed budget and shows a sharp rise near the critical loading (cascade fraction jumps >0.3 across a narrow budget band).
  - P3: Model divergence: for matched seed budget the greedy-optimal seed SET under Linear Threshold differs from that under Independent Cascade on the same graph (Jaccard overlap of seed sets < 0.8), i.e. the optimal targeting is model-specific.
*vs nearest built:* Nearest built is granovetter_threshold (single-population threshold distribution) and watts_cascade. Linear-Threshold-IM places per-node random thresholds on a weighted NETWORK and adds the seed-optimization layer plus the IC-vs-LT divergence test, none of which the single-population granovetter_threshold captures.

**`iterated_learning_kirby`** — Kirby 2001 / Kirby, Smith & Brighton 2004 — Iterated learning and compositional language (2001)
*framing:* genuine-agent · *difficulty:* high
*claim:* Transmission through a learning bottleneck drives a holistic mapping toward compositional grammar; with no bottleneck compositionality does not emerge.
*lockable predictions (draft):*
  - P1: compositionality increases over generations under a bottleneck: a structure metric (e.g. fraction of meaning space correctly generalized, or topographic/correlation measure) rises from near-chance to near-1 within the simulated generations (final >= 0.8).
  - P2: bottleneck is necessary: with no bottleneck (learner observes the full meaning-signal set each generation) compositionality does NOT systematically increase (final structure score stays < 0.4, significantly below the bottleneck condition).
  - P3: once compositional, the language transmits with high fidelity — adult-to-child transmission error drops to near 0 (expressivity over the full meaning space approaches 100%), a stable absorbing state.
*vs nearest built:* Nearest built is naming_game (population of agents negotiating a shared lexicon by pairwise interaction toward consensus). Iterated learning is a vertical, generation-to-generation transmission-chain model: a single learner per generation infers a grammar from a BOTTLENECKED sample and passes it on, and the emergent observable is COMPOSITIONAL STRUCTURE (generalization beyond seen data) gated by bottleneck size — not lexical consensus among peers. The bottleneck phase effect is a distinct lockable claim absent from the naming game.

**`tangled_nature`** — Christensen, di Collobiano, Hall & Jensen 2002 — Tangled Nature model (2002)
*framing:* genuine-agent · *difficulty:* high
*claim:* Evolving genotypes with random pairwise interactions self-organize into punctuated quasi-stable epochs that age (quake count grows ~log t).
*lockable predictions (draft):*
  - P1: dynamics are punctuated, not smooth: the time series of total population / diversity shows intermittent quiet epochs whose durations are heavy-tailed (epoch-length distribution is approximately power-law / log-normal, not exponential — KS test rejects exponential at p<0.05).
  - P2: the system 'ages': the number of quakes/transitions up to time t grows sub-linearly, approximately as log(t) (linear fit of cumulative transitions vs log t has R^2 >= 0.85).
  - P3: during a quiet epoch occupied genotypes form a small mutually-supporting core (a few species hold the bulk of the population: top-k genotypes carry >70% of individuals), and this core is replaced wholesale at a transition.
*vs nearest built:* Nearest built is bak_sneppen (and nk_landscape). Bak-Sneppen drives punctuated equilibrium via an abstract extremal rule on a fixed ring of fitness values with no genomes or populations; NK is a static fitness landscape. Tangled Nature is a genuine individual-based eco-evolutionary model: agents are genotypes in sequence space with reproduction, mutation and explicit random pairwise interaction couplings, and population sizes evolve. Its signature observables — log-time aging of quake counts and self-organized q-ESS epochs from real population dynamics — are distinct from Bak-Sneppen's avalanche statistics.

**`webworld_foodweb`** — Caldarelli, Higgs & McKane 1998 — Webworld coevolution model (1998)
*framing:* genuine-agent · *difficulty:* high
*claim:* Invasion/extinction assembly under a population-dynamics filter self-organizes a bounded food web: richness saturates, connectance stays low, and a few trophic levels emerge.
*lockable predictions (draft):*
  - P1: richness saturates: total species count rises then plateaus, with the plateau standard deviation < 25% of the plateau mean over the final third of the assembly run (bounded, not monotonically diverging).
  - P2: connectance is low and stable: mean links-per-species settles to a small finite value (e.g. ~2-4 prey per consumer) with <20% drift over the final third of the run.
  - P3: a finite trophic hierarchy emerges: the realized food web has >1 and <=~4-5 trophic levels at steady state (not a single trophic level, not unbounded chains).
*vs nearest built:* Nearest built is lotka_volterra (fixed 2-species interaction) and bak_sneppen (abstract evolution). Webworld is a community-ASSEMBLY model: new species with random feature vectors invade, predator-prey scores and a ratio-dependent functional response decide who persists, and an entire multi-trophic food-web topology self-organizes. The lockable observables are emergent network/ecosystem statistics (richness saturation, connectance, number of trophic levels) — graph-level community structure that no built model produces.

## Critic guidance — fold in before locking each batch
### Over-similar flags (tighten the gate or drop)
The critic flagged these as too close to an already-built model to count as a distinct reproduction unless each gets a quantitative gate a built model's rerun could NOT already pass. Treat as **drop-or-justify**:

| candidate | ~ existing | note |
|---|---|---|
| `sirs_waning_immunity (batch 8)` | sis (built) | SIS IS the limiting case of SIRS with zero immune period. The locked claim — 'stable nonzero endemic equilibrium for R0>1, replacing SIR burnout' — is exactly what sis-endemic already verifies (i*=1-1/R0). The only genuinely new gate would be 'endemic level rises with waning rate', a one-parameter sweep. Marked 'low' difficulty for good reason; weakest distinctness in the roadmap. |
| `linear_threshold_influence (batch 20)` | watts_cascade / granovetter_threshold (built) | The LT activation dynamics ARE the Granovetter/Watts fractional-threshold rule already built twice. The novel content is purely the submodularity/greedy-(1-1/e) optimization claim — an algorithmic result, not a new ABM. Also overlaps heavily with independent_cascade in batch 8 (same KKT 2003 paper); the two influence-max entries should arguably be one reproduction. |
| `pastor_satorras_vespignani_sis (batch 8)` | sis + barabasi_albert (both built) | Mechanically this is the built SIS dynamics run on the built BA generator. The vanishing-threshold result is a real and famous finding, so it survives as distinct, but it is an assembly of two existing components rather than new agent rules — review should confirm the finite-size threshold-scaling gate is non-trivial, else it collapses into 'sis on a network'. |
| `competitive_lotka_volterra_nspecies + rosenzweig_macarthur (batch 14)` | lotka_volterra (built) | Both are the same predator-prey/competition ODE family already built. Rosenzweig-MacArthur adds a Holling-II term (Hopf bifurcation) and n-species adds symmetric competition — genuinely different bifurcation claims, so defensible, but two LV variants in one batch plus the built base risks the suite looking padded with parameter-tweaks of one model. |
| `q_voter + noisy_voter_kirman (batch 7)` | voter (built) | Both are explicitly framed as variants of the built voter model. They survive because the locked claims are qualitatively new (nonlinear exit probability / discontinuous transition for q-voter; finite-size order-disorder transition for noisy). Acceptable as distinct, but they are the closest-to-base entries in batch 7 and need their distinguishing gates (hysteresis for q>=4; a_c~1/N scaling) to actually be measured, not just asserted. |
| `maslov_sneppen_rewiring (batch 11)` | watts_strogatz + erdos_renyi (built) | Degree-preserving double-edge-swap is a null-model generator, not a dynamical ABM. Low novelty as a standalone 'reproduction' — its scientific content (disassortativity significance) depends entirely on having a real network to compare against. Risk: it becomes a utility function dressed as a study. Distinct enough only if paired with a concrete biological-network null-test gate. |

### Famous omissions (consider swapping in for any dropped over-similar entry)
Iconic models missing from BOTH the built suite AND the batches above:

- **Conway-Reynolds Game of Life is built, but Langton's Ant / Langton's Lambda edge-of-chaos is missing** — The canonical demonstration that simple CA rules self-tune to a critical lambda parameter separating order and chaos; foundational to the whole complex-systems field and absent from both lists.
- **Wolfram elementary CA / Rule 110** — The most iconic 1D CA result (universality, four Wolfram classes); any 100-model classics suite that has Game of Life but no elementary-CA class taxonomy has a glaring gap.
- **Tit-for-Tat / Axelrod tournament winner is implicit in axelrod_ipd, but the GA-evolved strategy ecology is missing** — Canonical open-ended evolution of IPD strategies (finite-state machines, punctuated equilibria of strategy complexity); distinct from the fixed-strategy axelrod_ipd already built.
- **Garden / Tierra-style digital evolution** — The founding artificial-life open-ended-evolution model (self-replicating code, parasites, evolved optimization); iconic and unrepresented.
- **Prisoner's Dilemma on dynamic small-world is covered, but Kauffman Boolean (random) networks are missing** — NK is built but the RBN / Boolean-network ordered-critical-chaotic phase transition (K=2 criticality) is a separate canonical Kauffman model and a cornerstone of complexity science.
- **Tragedy-of-the-commons spatial resource model** — Common-pool-resource governance ABMs (Ostrom/Janssen lineage) are a canonical social-ecological strand entirely absent; distinct from public_goods which lacks the renewable-resource dynamics.
- **Reynolds Boids is built, but the Sakoda checkerboard (the proto-Schelling)** — Historically the first agent-based social segregation model, predating and distinct in attitude-matrix formulation from Schelling; a canonical origin-of-ABM entry.

### Dropped as duplicate during synthesis (already removed)
- `biham_middleton_levine` — Exact cross-domain duplicate: appears twice in the candidate list (identical BML 2D traffic CA). Kept one instance, dropped the second.
- `tangled_nature` — Exact cross-domain duplicate: appears twice (Christensen et al. 2002 Tangled Nature). Kept one instance, dropped the second.
- `kirman_ant_recruitment` — Folded into noisy_voter_kirman: same herding/bimodality-vs-unimodality finite-size transition driven by spontaneous switching destroying absorbing states. The two are near-identical lockable claims (ergodic stationary distribution, bimodal for weak noise); retaining both would be redundant. noisy_voter_kirman is the cleaner, more canonical statement.
- `seir_epidemic` — Trivial variant of built sir: adds one Exposed compartment; threshold R0=1 and final-size relation are explicitly UNCHANGED from SIR. Only delta is peak delay/flattening, too thin a distinct claim to fund a study-grade reproduction over the existing sir model.
- `friedkin_johnsen` — Near-duplicate of the bounded-confidence family (deffuant/hegselmann_krause) plus a closed-form linear-algebra steady state; the lambda->0 limit just recovers DeGroot consensus. Low distinctness as a standalone ABM — the load-bearing result is a matrix inversion, not emergent agent dynamics, and stubborn-agent persistent disagreement is already qualitatively covered by HK clustering.
- `tit_for_tat_evolution` — Duplicates the evolutionary-IPD claim space already covered jointly by built axelrod_ipd and the retained pavlov_wsls / image_scoring candidates; the shadow-of-the-future w-threshold for TFT stability is the canonical result that ultimatum/image-scoring/WSLS reproductions collectively already exercise. Lowest-distinctness member of the reciprocity cluster.

## Recommended path to a clean 100
1. **Prune** the ~6 over-similar flags above (or give each a gate that defeats a built-model rerun). That leaves comfortably more than 50 distinct survivors.
2. **Swap in** 3–5 of the famous omissions (Langton's Ant/λ, Wolfram Rule 110, Kauffman RBN, Sakoda proto-Schelling, a CPR/Ostrom commons model) — each is iconic and clearly distinct.
3. **Build in waves of 5**, lock-first, with one adversarial review pass per batch (the bottleneck the critic names is review/distinctness adjudication, not coding — so budget the review, not the build).
4. **Watch framing drift:** the network-generation family (Molloy-Reed/configuration, Price, Holme-Kim, Bianconi-Barabási, Maslov-Sneppen) is structurally one family; count them as distinct only where the *measured emergent property* differs, not just the generator knob.
