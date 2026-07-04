# Seattle SDOT Dynamic Congestion Validation Repro Pack

This fixture is a manifest-backed wrapper around the committed Seattle SDOT
2023 FLOWMAP count sample and official Seattle Streets centerline match pack.
It does not duplicate official raw data; it points at the existing bounded
centerline-match manifest and fixes deterministic dynamic congestion validation
parameters.

The pack proves that the existing dynamic congestion validation smoke can be
rerun from a manifest and audited with per-edge residual diagnostics. It does
not prove traffic-flow validity, congestion calibration, capacity inference, or
production traffic assignment.
