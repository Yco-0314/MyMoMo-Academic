# King County Road Closure Real Sample

This fixture is a bounded real official road-closure sample from King County
Emergency Management's public `RoadClosures_public` ArcGIS FeatureServer,
Closures layer.

It is committed as a small local JSON sample so tests do not query a live feed.
The sample exercises provenance, checksum verification, timestamp-to-tick
conversion, incident intake, edge matching, and dynamic incident event-effect
plumbing.

It does not prove traffic-flow validity, production map matching,
route-choice validation, incident calibration, or full live-feed support.
