# Spatial Rock-Paper-Scissors (cyclic dominance) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Genuine agent-based reproduction of the
May-Leonard / Reichenbach-Mobilia-Frey cyclic-dominance coexistence result. Honest:
falsified clauses would be reported as MISS; none were.

## What was run

A single three-species cyclic Lotka-Volterra model (R beats S beats P beats R) on an
`L x L` lattice, evaluated in two arms that differ in **exactly one thing — locality**:

- **Spatial arm** — interaction partners are the 4 periodic von-Neumann nearest
  neighbours (low/zero mobility: exchange rate `epsilon = 0`).
- **Well-mixed control** — the partner is a uniformly-random GLOBAL site every event;
  the lattice geometry is destroyed while every reaction rule is byte-for-byte identical.

The model is genuinely agent-based on `abm_auto._platform`: one `SiteAgent` per cell,
driven by an `AgentSet` scheduler in `random_order`; one generation (tick) = `L*L`
random Monte-Carlo events = the canonical Reichenbach-Mobilia-Frey timescale. Each event
draws a reaction type proportional to `(sigma, mu, epsilon)` and applies predation
(prey -> empty), reproduction (species fills an empty cell), or exchange (swap). A single
seeded `numpy.random.default_rng(seed)` drives the initial configuration and every
per-event choice, so each run is byte-reproducible.

## Locked configuration (fixed BEFORE running; not tuned)

- `L = 100` (10,000 cells), periodic von-Neumann lattice.
- Rates `sigma = 1.0` (selection/predation), `mu = 1.0` (reproduction),
  `epsilon = 0.0` (mobility/exchange — zero for the spatial arm; the well-mixed arm
  uses the SAME `epsilon=0.0` and differs ONLY by drawing global partners).
- `n_gen = 500` generations (= 5,000,000 events per run).
- 5 seeds per arm (`seed_base = 0`, seeds 0..4).
- Initial configuration: fully occupied, each cell a uniformly random species (equal
  thirds in expectation).
- **Grading metric (locked): number of surviving species** (a species "survives" if its
  final fraction > 0). Coexistence (P1) additionally requires each final fraction > 0.05.

The only difference between the two arms is locality; `L`, all rates, the run length, the
seeds, and the metric are identical and fixed. No tuning.

## Results (mean over 5 seeds)

| Arm        | #surviving species (mean) | per-seed #surviving | coexist (all 3 > 0.05) |
|------------|---------------------------|---------------------|------------------------|
| Spatial    | 3.00                      | [3, 3, 3, 3, 3]     | 5/5 = 100%             |
| Well-mixed | 1.00                      | [1, 1, 1, 1, 1]     | 0/5 = 0%               |

Mean final per-species fractions:

- **Spatial:** R ~ 0.322, P ~ 0.323, S ~ 0.298 — the three species partition the lattice
  into roughly equal thirds and persist. The spatial structure self-organises into
  entangled rotating domains (spiral waves in the canonical model); locally each species
  is chased by the one that beats it, so no single species can sweep the lattice.
- **Well-mixed:** the surviving species varies by seed (S in 4/5 seeds, P in 1/5), but in
  every seed exactly ONE species remains (mean fractions R 0.0 / P 0.2 / S 0.8 are just
  the empirical mix of which species happened to win). The mean-field/finite system
  performs a random walk in the density simplex and hits an absorbing boundary —
  biodiversity is lost.

## Verdicts (graded on the LOCKED metric)

- **P1 — spatial preserves coexistence: REPRO.** All three species have final fraction
  > 0.05 in 5/5 = 100% of seeds (>= 80% required).
- **P2 — well-mixed loses biodiversity: REPRO.** >= 1 species extinct in every well-mixed
  seed; the system collapses to exactly 1 survivor (max #surviving = 1).
- **P3 — contrast: REPRO.** Spatial #surviving (3.00) > well-mixed #surviving (1.00).

## Caveats (honest)

- **Finite-size coarsening.** On a finite lattice over a long enough run, coexistence is
  only *quasi*-stationary: the spiral domains coarsen and a finite system will eventually
  lose a species to demographic fluctuations (the same finite-size extinction the
  Reichenbach-Mobilia-Frey work characterises, with an extinction time that grows with the
  system size). At `L=100, n_gen=500` the spatial arm robustly coexists in all 5 seeds,
  but the claim is about the relevant timescale, not literal infinity; a much smaller `L`
  or a much longer run could still lose a species, and that would be reported honestly.
- **Zero-mobility spatial arm.** We set `epsilon = 0` for the cleanest spatial/well-mixed
  contrast. The Reichenbach-Mobilia-Frey result is richer: there is a critical mobility
  above which even the *spatial* lattice loses coexistence (the spirals outgrow the
  system). We do not sweep mobility here; the locked claim is the locality contrast at low
  mobility, and that is what is graded.
- **Scope.** This is a faithful reproduction of a published synthetic model; there is no
  real-world data. The contribution is whether the harness + lock-first discipline
  reproduce the coexistence-vs-extinction result and would catch an artifact, not a new
  empirical finding.

## Sources

- Reichenbach, T., Mobilia, M. & Frey, E. (2007) "Mobility promotes and jeopardizes
  biodiversity in rock-paper-scissors games", Nature 448:1046-1049.
  doi:10.1038/nature06095.
- Reichenbach, T., Mobilia, M. & Frey, E. (2008) "Self-organization of mobile populations
  in cyclic competition", J. Theor. Biol. 254(2):368-383. doi:10.1016/j.jtbi.2008.05.014.
- May, R.M. & Leonard, W.J. (1975) "Nonlinear aspects of competition between three
  species", SIAM J. Appl. Math. 29(2):243-253. doi:10.1137/0129022.
