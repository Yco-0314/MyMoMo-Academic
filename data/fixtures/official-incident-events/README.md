# Official Incident Event Intake Fixture

This directory contains a synthetic official-style incident-event fixture for
the Phase 1 intake and edge-matching bridge.

It is not a real official incident dataset. It exists to keep the manifest,
checksum, CSV loader, edge matching diagnostics, and gate behavior deterministic
in the open test suite.

Scientific boundary: this proves incident-event intake plumbing and edge-match
diagnostics only. It does not prove traffic-flow validity, production map
matching, or optimal incident management.
