"""Back-compat shim. ``_repro_bundle`` was promoted to the domain-agnostic base module
:mod:`abm_auto.repro_bundle` — the L3 gated-provenance bundle is a trust-layer primitive
(zero GIS concepts) reused by both GIS and closed extensions. This re-exports it so existing
``abm_auto.gis._repro_bundle`` importers keep working unchanged.
"""
from abm_auto.repro_bundle import *  # noqa: F401,F403
from abm_auto.repro_bundle import (  # noqa: F401  explicit, for `import ... as repro_bundle`
    SCHEMA,
    build_bundle,
    env_versions,
    git_commit,
    repro_bundle_integrity_gate,
    validate_repro_bundle,
    validate_repro_bundle_file,
    verdict_to_dict,
    write_bundle,
)
