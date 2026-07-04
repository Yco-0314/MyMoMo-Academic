# Traffic Count Fixture Pack

This directory contains a tiny local CSV fixture used to test manifest-backed
traffic-count plumbing. It is not official traffic data.

To use a real traffic-count source, download the CSV outside this repository,
project station coordinates into the same CRS as the target `GeoNetwork`, copy
`manifest.example.json`, and point `csv_path` at the local CSV. This phase never
downloads data, reprojects coordinates, or performs full map matching.
