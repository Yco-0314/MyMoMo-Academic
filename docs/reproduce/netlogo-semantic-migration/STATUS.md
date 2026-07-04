# NetLogo Semantic Migration Status

NetLogo Semantic Migration Gate Phase 1 adds a manifest-driven migration proof
over the existing native NetLogo semantic cells.

Implemented surface:

- `abm_auto.netlogo_migration`
- `validate_netlogo_migration_spec(...)`
- `run_netlogo_semantic_migration(...)`
- `netlogo_semantic_migration_to_mir(...)`
- `netlogo_semantic_migration_gate(...)`

Seed fixture:

- `docs/reproduce/netlogo-semantic-migration/example-spec.json`

Boundary:

This phase migrates a small declared semantic manifest into `NetLogoWorld` and a
MIR summary. It is not a NetLogo parser, not NetLogo procedure execution, not
full NetLogo compatibility, and not a codegen template.
