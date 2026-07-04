# Incident Timestamp Clock Map Fixture

This fixture is a synthetic official-style incident interval with ISO-8601
timestamps. It exists to test deterministic timestamp-to-simulation-tick
conversion before incident rows are passed to the existing edge-matching intake.

It does not contain a real official incident feed, does not perform edge
matching, and does not claim traffic-flow validity, production map matching,
incident calibration, route-choice validity, or optimal incident management.
