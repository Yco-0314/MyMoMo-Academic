"""Faithful agent-based reproductions of classic ABMs on the neutral platform
``abm_auto._platform``, each run against pre-registered locked predictions with honest
REPRO/MISS verdicts + L3 reproduction bundles (see docs/studies/<name>/).

Batch 1 (network/coordination):
  - watts_cascade         — Watts 2002 global cascades (cascade window)
  - complex_contagion     — Centola & Macy 2007 (weakness of long ties)
  - granovetter_threshold — Granovetter 1978 threshold model

Batch 2 (segregation / culture / diffusion / games / opinion):
  - schelling             — Schelling 1971 segregation
  - axelrod_culture       — Axelrod 1997 dissemination of culture
  - bass_diffusion        — Bass 1969 diffusion
  - nowak_may_pd          — Nowak & May 1992 spatial prisoner's dilemma
  - deffuant              — Deffuant et al. 2000 bounded confidence

Batch 3 (inequality / games / violence / opinion / epidemics):
  - sugarscape            — Epstein & Axtell 1996 (emergent wealth inequality / Gini)
  - axelrod_ipd           — Axelrod 1984 IPD round-robin tournament (TFT / nice strategies)
  - epstein_civil_violence— Epstein 2002 civil violence (punctuated bursts / deterrence)
  - sznajd                — Sznajd-Weron & Sznajd 2000 opinion ("united we stand")
  - sir                   — SIR epidemic threshold (R0=beta/gamma; outbreak iff R0>1)

Batch 4 (networks / epidemics):
  - erdos_renyi           — Erdős–Rényi giant component (network generation)
  - voter                 — Voter model fixation (mean-field; P(all-up)=initial density)
  - watts_strogatz        — Watts-Strogatz small-world transition
  - barabasi_albert       — Barabasi-Albert preferential attachment and hubs
  - sis                   — SIS endemic threshold

Batch 4 / wave 2 (cooperation games / opinion):
  - hawk_dove             — Maynard Smith & Price Hawk-Dove mixed ESS p*=V/C
  - public_goods          — Fehr & Gächter 2000/2002 public goods + peer punishment
                            (cooperation collapses without punishment, sustained with)
  - hegselmann_krause     — HK bounded-confidence consensus / fragmentation
  - galam                 — Galam majority-rule tipping and tie-bias minority spreading
  - minority_game         — Challet-Zhang Minority Game volatility vs alpha

Batch 4 / wave 3 (collective motion / SOC / markets / language / traffic):
  - nagel_schreckenberg   — Nagel & Schreckenberg 1992 freeway traffic (fundamental
                            diagram: interior flow maximum, free-flow->jam, spontaneous jams)
  - btw_sandpile          — Bak, Tang & Wiesenfeld 1987 sandpile (SOC; CELLULAR AUTOMATON,
                            NOT agent-stepping — power-law avalanches, tau~1.2)

Batch 5 / wave A (phase transitions / sync / SOC):
  - ising                 — Onsager 1944 2D Ising / Glauber dynamics (genuine agent-based:
                            SpinAgent per site; ferromagnetic order-disorder transition at
                            T_c = 2/ln(1+sqrt(2)) ≈ 2.269)

Batch 5 / wave B (ecology / cooperation / coordination / genetics):
  - lotka_volterra        — Lotka 1925 / Volterra 1926 agent predator-prey (NetLogo
                            wolf-sheep-grass: PreyAgent + PredatorAgent on a toroidal grid,
                            grass = carrying capacity; sustained oscillations with the
                            predator lagging the prey; extinction-prone, survival fraction
                            reported honestly)

Batch 6 / wave A (evolution / fitness landscapes / ecology / collective motion):
  - wright_fisher         — Wright-Fisher genetic drift (allele fixation; no selection)
  - nk_landscape          — Kauffman NK rugged-fitness landscape (ruggedness vs K)
  - bak_sneppen           — Bak-Sneppen coevolution (SOC; punctuated equilibrium, min-site)
  - daisyworld            — Watson & Lovelock 1983 (planetary temperature homeostasis)
  - ant_foraging          — Ant pheromone trail foraging (stigmergy; shortest-path emerges)
  - boids                 — Reynolds 1987 flocking (genuine agent-based: 3-rule steering;
                            alignment creates the common heading)

Batch 6 / wave B (SOC / norms / social balance / group formation / collective decision):
  - olami_feder_christensen — Olami-Feder-Christensen 1992 earthquakes (SOC; driven-threshold
                            CELLULAR AUTOMATON, NOT agent-stepping — power-law events,
                            alpha-dependent tail)
  - axelrod_norms         — Axelrod 1986 norms/metanorms (genuine agent-based; metanorms RAISE
                            enforcement vs the plain norm — comparative claim)
  - heider_balance        — Antal-Krapivsky-Redner 2005 social balance (SIGNED-NETWORK
                            dynamics, NOT agent-stepping — frustration falls monotonically to a
                            balanced 2-faction absorbing state)
  - seceder               — Dittrich et al. 2000 seceder model (genuine agent-based; outlier
                            reproduces -> spontaneous persistent multi-cluster group formation)
  - standing_ovation      — Miller & Page 2004 standing ovation (genuine agent-based; quality
                            threshold + spatial conformity amplify to ovation/no-ovation)

Batch 7 / wave A (opinion dynamics beyond voter):
  - q_voter               — Castellano-Munoz-Pastor-Satorras nonlinear q-panel voter
  - noisy_voter_kirman    — noisy voter/Kirman herding vs centred stationary regimes
  - abrams_strogatz_language — Abrams-Strogatz status-asymmetric language competition

Batch 7 / wave B (Bayesian discrete-action opinion / distance-weighted social impact):
  - coda_continuous_opinions — Martins CODA: discrete-action Bayesian updating diverges to
                            certainty (extremism), inverting bounded-confidence averaging
  - social_impact_theory  — Nowak-Szamrej-Latane dynamic social impact (clustering REPRO;
                            minority-survival honest MISS at alpha=2 global influence)

Batch 8 (epidemics / rumor / cascades / influence on networks):
  - bikhchandani_information_cascade — BHW 1992 rational-Bayesian herd; cascades form a.s. and
                            can be WRONG (P(incorrect|cascade)=(1-p)^2/(p^2+(1-p)^2))
  - maki_thompson_rumor   — Maki-Thompson rumor: rate-invariant ~0.203 never-hear constant
                            (hybrid CTMC; distinct from SIR's rate-dependent final size)
  - newman_network_sir    — Newman 2002 SIR = bond percolation; T_c=<k>/(<k^2>-<k>),
                            heterogeneity collapses the threshold (network-generation)
  - independent_cascade   — Kempe-Kleinberg-Tardos IC: percolation transition + submodular
                            spread + (1-1/e) greedy influence-max (hybrid)
  - pastor_satorras_vespignani — PSV 2001 SIS on scale-free: vanishing threshold lambda_c=<k>/<k^2>
                            on BA vs finite on ER (2/3 REPRO; P1 bar too tight for finite N)

Batch 9 (evolution of cooperation / reciprocity games):
  - snowdrift_game        — Hauert-Doebeli 2004: spatial structure INHIBITS cooperation (f_lat<1-r,
                            opposite sign to spatial PD); gate confirms stochastic-replicator specific
  - stag_hunt             — coordination game: bistable basins, risk-dominant equilibrium larger basin
  - pavlov_wsls           — Nowak-Sigmund WSLS beats TFT under noise+evolution (2/3; P2 bar was 4.5
                            but faithful WSLS-vs-ALLC = (R+T)/2 = 4.0)
  - image_scoring         — Nowak-Sigmund 1998 indirect reciprocity: cooperation needs info q>c/b
                            (1/3; P1/P3 honest MISS — mis-specified locked protocol, not a bug)
  - ultimatum_fairness    — Nowak-Page-Sigmund 2000: reputation drives offers from rational-0 to fair

Designs: docs/superpowers/specs/2026-06-29-classic-network-abm-reproductions-design.md
(batch 1), docs/superpowers/specs/2026-06-29-classic-abm-reproductions-batch2-design.md
(batch 2), docs/superpowers/specs/2026-06-29-classic-abm-reproductions-batch3-design.md
(batch 3), and docs/superpowers/specs/2026-06-29-classic-abm-reproductions-batch4-design.md
(batch 4), plus docs/superpowers/specs/2026-06-29-classic-abm-reproductions-batch4-wave2-design.md
(batch 4 / wave 2)."""
