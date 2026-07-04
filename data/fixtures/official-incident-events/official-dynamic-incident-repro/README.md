# Official Dynamic Incident Repro Pack

This fixture is a manifest-backed wrapper around the synthetic official-style
incident event intake fixture and the official dynamic incident event-effect
smoke. It does not duplicate event rows; it points at the existing incident
intake manifest and fixes deterministic validation parameters.

The pack proves that the existing dynamic incident validation smoke can be
rerun from a manifest with locked event-effect diagnostics. It does not prove
traffic-flow validity, production map matching, real incident calibration,
route optimality, or optimal incident management.
